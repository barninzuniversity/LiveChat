from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from chat.models import Post, Profile, Comment, PostReaction, CommentReaction, PostShare, Repost, ChatRoom, Message, BlockedPost, FriendList, FriendRequest


class Command(BaseCommand):
    help = 'Delete all users and posts data from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-superuser',
            action='store_true',
            help='Keep superusers in the database',
        )

    def handle(self, *args, **options):
        keep_superuser = options.get('keep_superuser', False)
        
        # Clear all related models first
        self.stdout.write('Deleting all related data...')
        
        # Delete chat-related data
        Message.objects.all().delete()
        self.stdout.write('Messages deleted.')
        
        ChatRoom.objects.all().delete()
        self.stdout.write('Chat rooms deleted.')
        
        # Delete post-related data
        PostShare.objects.all().delete()
        self.stdout.write('Post shares deleted.')
        
        Repost.objects.all().delete()
        self.stdout.write('Reposts deleted.')
        
        CommentReaction.objects.all().delete()
        self.stdout.write('Comment reactions deleted.')
        
        Comment.objects.all().delete()
        self.stdout.write('Comments deleted.')
        
        PostReaction.objects.all().delete()
        self.stdout.write('Post reactions deleted.')
        
        BlockedPost.objects.all().delete()
        self.stdout.write('Blocked posts deleted.')
        
        Post.objects.all().delete()
        self.stdout.write('Posts deleted.')
        
        # Delete friend-related data
        FriendRequest.objects.all().delete()
        self.stdout.write('Friend requests deleted.')
        
        # Try to delete FriendList if it exists
        try:
            FriendList.objects.all().delete()
            self.stdout.write('Friend lists deleted.')
        except:
            self.stdout.write('No friend lists to delete.')
        
        # Delete user profiles and users
        # Keep superusers if requested
        if keep_superuser:
            # Get non-superuser users
            non_superusers = User.objects.filter(is_superuser=False)
            
            # Get their profile IDs
            profile_ids = Profile.objects.filter(user__in=non_superusers).values_list('id', flat=True)
            
            # Delete those profiles
            Profile.objects.filter(id__in=profile_ids).delete()
            self.stdout.write('Non-superuser profiles deleted.')
            
            # Delete non-superuser users
            count = non_superusers.count()
            non_superusers.delete()
            self.stdout.write(f'{count} non-superuser users deleted (kept superusers).')
        else:
            # Delete all profiles and users
            Profile.objects.all().delete()
            self.stdout.write('All profiles deleted.')
            
            count = User.objects.count()
            User.objects.all().delete()
            self.stdout.write(f'All {count} users deleted.')
        
        self.stdout.write(self.style.SUCCESS('Successfully cleared all user and post data!')) 