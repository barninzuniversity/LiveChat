from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.http import JsonResponse, StreamingHttpResponse, HttpResponseForbidden, HttpResponseBadRequest, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
import json, asyncio, time
from datetime import datetime
from channels.db import database_sync_to_async
from .models import Profile, FriendRequest, Post, ChatRoom, Message, BlockedPost, PostReaction, Comment, CommentReaction, PostShare, Repost, FriendList
from .forms import ProfileForm, PostForm
from django.db.models.functions import Now
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.backends.signals import connection_created
from django.db.utils import OperationalError
from django.db.models import Q
from django.template.loader import render_to_string
from django.middleware.csrf import get_token
from django.db.utils import IntegrityError

# Dictionary to store message queues for each chat room
message_queues = {}

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully. You can now log in.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def home(request):
    """Display the home feed with posts"""
    user_profile = request.user.profile
    blocked_users = user_profile.blocked_users.all()
    
    # Get friend IDs to filter posts
    friend_connections, created = FriendList.objects.get_or_create(user=user_profile)
    friends = friend_connections.friends.all()
    
    # Combine the user's and friends' profiles for the feed
    feed_profiles = list(friends) + [user_profile]
    
    # Query posts from the user and their friends, excluding blocked users
    posts = Post.objects.filter(
        author__in=feed_profiles
    ).exclude(
        author__in=blocked_users
    ).order_by('-created_at')
    
    # Check user reactions for each post
    for post in posts:
        post.user_reaction = PostReaction.objects.filter(post=post, user=user_profile).first()
        # Add user reaction info to comments
        for comment in post.comments.all():
            comment.user_has_reacted = CommentReaction.objects.filter(comment=comment, user=user_profile).exists()
    
    # Friend requests
    friend_requests = FriendRequest.objects.filter(to_user=user_profile, status='pending')
    
    # Process post creation form
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = user_profile
            post.save()
            messages.success(request, "Post created successfully!")
            return redirect('home')
    else:
        form = PostForm()
    
    context = {
        'posts': posts,
        'friend_requests': friend_requests,
        'form': form,
    }
    
    return render(request, 'chat/home.html', context)

@login_required
def profile_detail(request, username):
    user = get_object_or_404(User, username=username)
    profile = user.profile
    
    # Get user's own posts - use .all() to reset ordering
    own_posts = Post.objects.filter(author=profile).all()
    
    # Get posts that the user reposted
    reposted_post_ids = Repost.objects.filter(repost__author=profile).values_list('original_post_id', flat=True)
    reposted_posts = Post.objects.filter(id__in=reposted_post_ids).all()
    
    # Combined posts (own + reposted)
    posts = own_posts.union(reposted_posts).order_by('-created_at')
    
    # Check friend status
    is_friend = request.user.profile.friends.filter(id=profile.id).exists()
    
    # Check if friend request exists
    friend_request_sent = FriendRequest.objects.filter(
        from_user=request.user.profile,
        to_user=profile,
        status='pending'
    ).exists()
    
    friend_request_received = FriendRequest.objects.filter(
        from_user=profile,
        to_user=request.user.profile,
        status='pending'
    ).exists()
    
    context = {
        'profile': profile,
        'posts': posts,
        'is_friend': is_friend,
        'is_self': request.user == user,
        'friend_request_sent': friend_request_sent,
        'friend_request_received': friend_request_received,
    }
    return render(request, 'chat/profile_detail.html', context)

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile_detail', username=request.user.username)
    else:
        form = ProfileForm(instance=request.user.profile)
    
    return render(request, 'chat/edit_profile.html', {'form': form})

@login_required
def send_friend_request(request, username):
    to_user = get_object_or_404(User, username=username)
    from_user = request.user.profile
    
    if from_user == to_user.profile:
        messages.error(request, "You cannot send a friend request to yourself.")
        return redirect('profile_detail', username=username)
    
    if from_user.friends.filter(id=to_user.profile.id).exists():
        messages.info(request, "You are already friends with this user.")
        return redirect('profile_detail', username=username)
    
    friend_request, created = FriendRequest.objects.get_or_create(
        from_user=from_user,
        to_user=to_user.profile
    )
    
    if created:
        messages.success(request, f"Friend request sent to {to_user.username}.")
    else:
        messages.info(request, f"Friend request to {to_user.username} already exists.")
    
    return redirect('profile_detail', username=username)

@login_required
def respond_friend_request(request, request_id, action):
    friend_request = get_object_or_404(FriendRequest, id=request_id, to_user=request.user.profile)
    
    if action == 'accept':
        friend_request.status = 'accepted'
        friend_request.save()
        
        # Add to friends list (both ways due to symmetrical=True)
        request.user.profile.friends.add(friend_request.from_user)
        
        messages.success(request, f"You are now friends with {friend_request.from_user.user.username}.")
    
    elif action == 'reject':
        friend_request.status = 'rejected'
        friend_request.save()
        messages.info(request, f"Friend request from {friend_request.from_user.user.username} rejected.")
    
    return redirect('home')

@login_required
def chat_list(request):
    user_profile = request.user.profile
    chat_rooms = ChatRoom.objects.filter(participants=user_profile)
    
    context = {
        'chat_rooms': chat_rooms
    }
    return render(request, 'chat/chat_list.html', context)

@login_required
def create_or_get_direct_chat(request, username):
    other_user = get_object_or_404(User, username=username)
    user_profile = request.user.profile
    other_profile = other_user.profile
    
    # Check if users are friends
    if not user_profile.friends.filter(id=other_profile.id).exists():
        messages.error(request, "You can only chat with your friends.")
        return redirect('profile_detail', username=username)
    
    # Find existing direct chat
    common_chats = ChatRoom.objects.filter(
        participants=user_profile,
        is_group_chat=False
    ).filter(
        participants=other_profile
    )
    
    if common_chats.exists():
        chat_room = common_chats.first()
    else:
        # Create new chat room
        chat_room = ChatRoom.objects.create(is_group_chat=False)
        chat_room.participants.add(user_profile, other_profile)
    
    return redirect('chat_room', room_id=chat_room.id)

@login_required
def chat_room(request, room_id):
    chat_room = get_object_or_404(ChatRoom, id=room_id)
    user_profile = request.user.profile
    
    # Check if user is participant
    if not chat_room.participants.filter(id=user_profile.id).exists():
        messages.error(request, "You cannot access this chat room.")
        return redirect('chat_list')
    
    # Get messages
    messages_list = Message.objects.filter(room=chat_room).order_by('timestamp')
    
    # Mark unread messages as read
    unread_messages = messages_list.filter(
        is_read=False
    ).exclude(sender=user_profile)
    
    for msg in unread_messages:
        msg.is_read = True
        msg.save()
    
    # Get other participants
    other_participants = chat_room.participants.exclude(id=user_profile.id)
    
    context = {
        'chat_room': chat_room,
        'messages': messages_list,
        'user_profile': user_profile,
        'other_participants': other_participants,
    }
    
    return render(request, 'chat/chat_room.html', context)

@login_required
def friends_list(request):
    user_profile = request.user.profile
    friends = user_profile.friends.all()
    
    context = {
        'friends': friends
    }
    
    return render(request, 'chat/friends_list.html', context)

@login_required
def search_users(request):
    query = request.GET.get('q', '')
    if query:
        users = User.objects.filter(username__icontains=query).exclude(id=request.user.id)
    else:
        users = User.objects.none()
    
    context = {
        'users': users,
        'query': query
    }
    
    return render(request, 'chat/search_users.html', context)

@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    # Check if the user is the author of the post
    if post.author.user != request.user:
        messages.error(request, "You cannot delete posts that aren't yours.")
        return redirect('home')
    
    if request.method == 'POST':
        post.delete()
        messages.success(request, "Post deleted successfully.")
        
    return redirect('home')

@login_required
def block_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    user_profile = request.user.profile
    
    # Cannot block your own post
    if post.author == user_profile:
        messages.error(request, "You cannot block your own post.")
        return redirect('home')
    
    # Check if already blocked
    block, created = BlockedPost.objects.get_or_create(user=user_profile, post=post)
    
    if created:
        messages.success(request, f"Post by {post.author.user.username} has been blocked.")
    else:
        messages.info(request, f"Post was already blocked.")
    
    return redirect('home')

@login_required
def block_user(request, username):
    target_user = get_object_or_404(User, username=username)
    user_profile = request.user.profile
    target_profile = target_user.profile
    
    # Cannot block yourself
    if target_user == request.user:
        messages.error(request, "You cannot block yourself.")
        return redirect('home')
    
    # Add to blocked users
    user_profile.blocked_users.add(target_profile)
    
    # Remove from friends if they are friends
    if user_profile.friends.filter(id=target_profile.id).exists():
        user_profile.friends.remove(target_profile)
        messages.info(request, f"{target_user.username} has been removed from your friends.")
    
    # Delete any pending friend requests
    FriendRequest.objects.filter(
        (Q(from_user=user_profile) & Q(to_user=target_profile)) |
        (Q(from_user=target_profile) & Q(to_user=user_profile))
    ).delete()
    
    messages.success(request, f"{target_user.username} has been blocked.")
    
    # Redirect to previous page or home
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def unblock_user(request, username):
    target_user = get_object_or_404(User, username=username)
    user_profile = request.user.profile
    target_profile = target_user.profile
    
    # Remove from blocked users
    user_profile.blocked_users.remove(target_profile)
    
    messages.success(request, f"{target_user.username} has been unblocked.")
    
    return redirect('home')

@login_required
def blocked_users(request):
    user_profile = request.user.profile
    blocked = user_profile.blocked_users.all()
    
    context = {
        'blocked_users': blocked
    }
    
    return render(request, 'chat/blocked_users.html', context)

@login_required
def get_messages(request, room_id):
    """
    HTMX endpoint to get messages for a chat room
    """
    chat_room = get_object_or_404(ChatRoom, id=room_id)
    user_profile = request.user.profile
    
    # Check if user is participant
    if not chat_room.participants.filter(id=user_profile.id).exists():
        return HttpResponseForbidden("Access denied")
    
    # Get messages
    messages = Message.objects.filter(room=chat_room).order_by('timestamp')
    
    # Mark unread messages as read
    unread_messages = messages.filter(
        is_read=False
    ).exclude(sender=user_profile)
    
    for msg in unread_messages:
        msg.is_read = True
        msg.save()
    
    # Render only the messages
    return render(request, 'chat/messages.html', {
        'messages': messages,
        'user_profile': user_profile
    })

@login_required
def send_message(request, room_id):
    """
    HTMX endpoint to send a message to a chat room
    """
    if request.method == 'POST':
        try:
            message_content = request.POST.get('message', '')
            attachment = request.FILES.get('attachment')
            
            # Require at least one of message content or attachment
            if not message_content and not attachment:
                return HttpResponseBadRequest("Message content or attachment is required")
            
            chat_room = get_object_or_404(ChatRoom, id=room_id)
            user_profile = request.user.profile
            
            # Check if user is participant
            if not chat_room.participants.filter(id=user_profile.id).exists():
                return HttpResponseForbidden("Access denied")
            
            # Create message
            message = Message(
                room=chat_room,
                sender=user_profile,
                content=message_content
            )
            
            # Handle file upload
            if attachment:
                # Check if it's an image or other file
                if attachment.content_type.startswith('image/'):
                    message.image = attachment
                else:
                    message.file = attachment
            
            message.save()
            
            # Get all messages and return them
            messages_list = Message.objects.filter(room=chat_room).order_by('timestamp')
            
            # Return all messages after sending
            return render(request, 'chat/messages.html', {
                'messages': messages_list,
                'user_profile': user_profile
            })
            
        except Exception as e:
            print(f"Error in send_message: {str(e)}")
            import traceback
            traceback.print_exc()
            return HttpResponseBadRequest(str(e))
    
    return HttpResponseNotAllowed("Method not allowed")

@login_required
async def message_stream(request, room_id):
    """
    Server-Sent Events (SSE) endpoint to stream messages for a chat room
    """
    try:
        print(f"Setting up SSE connection for room {room_id}, user {request.user.username}")
        
        # Use database_sync_to_async for all database operations in async context
        @database_sync_to_async
        def get_chat_room():
            return get_object_or_404(ChatRoom, id=room_id)
        
        @database_sync_to_async
        def get_user_profile(request):
            return request.user.profile
        
        @database_sync_to_async
        def check_user_access(chat_room, user_profile):
            return chat_room.participants.filter(id=user_profile.id).exists()
        
        # Get the chat room and user profile asynchronously
        chat_room = await get_chat_room()
        user_profile = await get_user_profile(request)
        
        # Check if user is participant
        has_access = await check_user_access(chat_room, user_profile)
        if not has_access:
            print(f"Access denied for user {request.user.username} to room {room_id}")
            return StreamingHttpResponse("Access denied", status=403)
        
        room_key = f'chat_{room_id}'
        client_id = f"{request.user.username}_{int(time.time())}"
        print(f"Client {client_id} connected to room {room_id}")
        
        # Initialize the queue for this room if it doesn't exist
        if room_key not in message_queues:
            message_queues[room_key] = []
        
        # Send initial connection message
        connection_message = {
            'type': 'connection',
            'message': f"Connected to chat room {room_id}",
            'timestamp': datetime.now().strftime("%I:%M %p")
        }
        
        # Send all existing messages in the queue to this new client
        # This ensures the client gets any messages sent while they were disconnected
        async def event_stream():
            try:
                # Send initial connection confirmation
                print(f"Sending connection message to {client_id}")
                yield f"data: {json.dumps(connection_message)}\n\n"
                
                # First, send any pending messages in the queue
                if room_key in message_queues and message_queues[room_key]:
                    for message_data in message_queues[room_key]:
                        yield f"data: {json.dumps(message_data)}\n\n"
                
                # Keep a pointer to the end of current messages
                message_index = len(message_queues.get(room_key, []))
                last_check = time.time()
                
                # Main event loop
                while True:
                    try:
                        # Check if there are new messages in the queue
                        if room_key in message_queues:
                            current_messages = message_queues[room_key]
                            while message_index < len(current_messages):
                                message_data = current_messages[message_index]
                                yield f"data: {json.dumps(message_data)}\n\n"
                                message_index += 1
                                print(f"Sent message {message_index} to client {client_id}")
                        
                        # Send a ping every 15 seconds to keep the connection alive
                        if time.time() - last_check > 15:
                            print(f"Sending ping to client {client_id}")
                            yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                            last_check = time.time()
                        
                        # Sleep to avoid CPU hogging
                        await asyncio.sleep(0.2)
                    except Exception as e:
                        print(f"Error in event loop for client {client_id}: {str(e)}")
                        yield f"data: {json.dumps({'type': 'error', 'message': f'Stream error: {str(e)}'})}\n\n"
                        # Continue the loop rather than breaking, to keep the connection alive
                        await asyncio.sleep(1)
            except Exception as e:
                print(f"SSE stream terminated for client {client_id}: {str(e)}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        print(f"Returning StreamingHttpResponse for client {client_id}")
        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        # Add headers to prevent caching
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
    except Exception as e:
        print(f"Error setting up SSE stream: {str(e)}")
        import traceback
        traceback.print_exc()
        return StreamingHttpResponse(
            f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n",
            content_type='text/event-stream'
        )

@login_required
def add_post_reaction(request, post_id):
    """Add a reaction to a post"""
    if request.method == 'POST':
        reaction_type = request.POST.get('reaction_type', 'like')
        post = get_object_or_404(Post, id=post_id)
        user_profile = request.user.profile
        
        try:
            # Check if user already reacted to this post
            existing_reaction = PostReaction.objects.filter(post=post, user=user_profile).first()
            
            if existing_reaction:
                # If the reaction is the same, remove it (toggle off)
                if existing_reaction.reaction_type == reaction_type:
                    existing_reaction.delete()
                    return JsonResponse({'status': 'success', 'action': 'removed', 'count': post.reactions.count()})
                else:
                    # Update to new reaction type
                    existing_reaction.reaction_type = reaction_type
                    existing_reaction.save()
                    return JsonResponse({'status': 'success', 'action': 'updated', 'type': reaction_type, 'count': post.reactions.count()})
            else:
                # Create new reaction
                PostReaction.objects.create(
                    post=post,
                    user=user_profile,
                    reaction_type=reaction_type
                )
                return JsonResponse({'status': 'success', 'action': 'added', 'type': reaction_type, 'count': post.reactions.count()})
        except IntegrityError:
            # If there's a race condition (user double-clicked), handle it gracefully
            # Just get the current reaction count and return it
            return JsonResponse({'status': 'success', 'action': 'exists', 'count': post.reactions.count()})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

@login_required
def add_comment(request, post_id):
    """Add a comment to a post"""
    if request.method == 'POST':
        content = request.POST.get('content')
        if not content:
            return JsonResponse({'status': 'error', 'message': 'Comment content is required'}, status=400)
        
        post = get_object_or_404(Post, id=post_id)
        user_profile = request.user.profile
        
        # Create comment
        comment = Comment.objects.create(
            post=post,
            author=user_profile,
            content=content
        )
        
        # Set user reaction info for template
        comment.user_has_reacted = False
        
        # Render the comment HTML
        html = render_to_string('chat/comment.html', {
            'comment': comment,
            'user_profile': user_profile,
            'csrf_token': get_token(request)
        }, request=request)
        
        return JsonResponse({
            'status': 'success', 
            'html': html, 
            'comment_id': comment.id, 
            'count': post.comments.count()
        })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

@login_required
def add_comment_reaction(request, comment_id):
    """Add a reaction to a comment"""
    if request.method == 'POST':
        reaction_type = request.POST.get('reaction_type', 'like')
        comment = get_object_or_404(Comment, id=comment_id)
        user_profile = request.user.profile
        
        # Check if user already reacted to this comment
        existing_reaction = CommentReaction.objects.filter(comment=comment, user=user_profile).first()
        
        if existing_reaction:
            # If the reaction is the same, remove it (toggle off)
            if existing_reaction.reaction_type == reaction_type:
                existing_reaction.delete()
                return JsonResponse({'status': 'success', 'action': 'removed', 'count': comment.reactions.count()})
            else:
                # Update to new reaction type
                existing_reaction.reaction_type = reaction_type
                existing_reaction.save()
                return JsonResponse({
                    'status': 'success', 
                    'action': 'updated', 
                    'type': reaction_type, 
                    'count': comment.reactions.count()
                })
        else:
            # Create new reaction
            CommentReaction.objects.create(
                comment=comment,
                user=user_profile,
                reaction_type=reaction_type
            )
            return JsonResponse({
                'status': 'success', 
                'action': 'added', 
                'type': reaction_type, 
                'count': comment.reactions.count()
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

@login_required
def share_dialog(request, post_id):
    """Show dialog to share a post with friends"""
    post = get_object_or_404(Post, id=post_id)
    user_profile = request.user.profile
    
    # Get list of friends to share with
    friends = user_profile.friends.all()
    
    return render(request, 'chat/share_dialog.html', {
        'post': post,
        'friends': friends
    })

@login_required
def share_post(request, post_id):
    """Share a post with selected friends"""
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        user_profile = request.user.profile
        
        # Get share recipients
        recipient_ids = request.POST.getlist('share_with')
        comment = request.POST.get('comment', '')
        
        if not recipient_ids:
            messages.warning(request, "Please select at least one friend to share with.")
            return redirect('share_dialog', post_id=post_id)
        
        # Create shares for each recipient
        for recipient_id in recipient_ids:
            recipient = get_object_or_404(Profile, id=recipient_id)
            
            # Create the share
            PostShare.objects.create(
                post=post,
                shared_by=user_profile,
                shared_with=recipient,
                comment=comment
            )
        
        messages.success(request, f"Post shared with {len(recipient_ids)} friend{'s' if len(recipient_ids) > 1 else ''}!")
        return redirect('home')
    
    # Handle GET request (redirect to dialog)
    return redirect('share_dialog', post_id=post_id)

@login_required
def repost(request, post_id):
    """Repost a post"""
    original_post = get_object_or_404(Post, id=post_id)
    user_profile = request.user.profile
    
    if request.method == 'POST':
        content = request.POST.get('content', f"Reposted from {original_post.author.user.username}")
        
        # Create the repost as a new post
        repost = Post.objects.create(
            author=user_profile,
            content=content
        )
        
        # Create relationship between original and repost
        Repost.objects.create(
            original_post=original_post,
            repost=repost
        )
        
        messages.success(request, "Post has been reposted to your profile!")
        return redirect('home')
    
    return render(request, 'chat/repost_form.html', {
        'post_id': post_id,
        'original_post': original_post
    })

@login_required
def set_dark_mode(request):
    """Save dark mode preference for the user"""
    if request.method == 'POST':
        # Get the dark mode preference from the request
        dark_mode = request.POST.get('dark_mode', 'off')
        
        # Store in session
        request.session['dark_mode'] = dark_mode == 'on'
        
        # Redirect back to the referring page or home
        referer = request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        return redirect('home')
    
    # If not a POST request, redirect to home
    return redirect('home')

@login_required
def get_comments(request, post_id):
    """Get comments for a post with HTMX"""
    post = get_object_or_404(Post, id=post_id)
    user_profile = request.user.profile
    
    # Get all comments for the post
    comments = post.comments.all().order_by('-created_at')
    
    # Add user reaction info for each comment
    for comment in comments:
        comment.user_has_reacted = CommentReaction.objects.filter(
            comment=comment, 
            user=user_profile
        ).exists()
    
    context = {
        'post': post,
        'comments': comments,
        'user_profile': user_profile
    }
    
    # Check if the request is from HTMX
    if request.headers.get('HX-Request'):
        return render(request, 'chat/comments_list.html', context)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
