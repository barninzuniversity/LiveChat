// Post and Comment Reactions JS
document.addEventListener('DOMContentLoaded', function() {
  // Handle post reactions
  setupPostReactions();
  
  // Handle comment submissions
  setupCommentSubmission();
  
  // Handle comment reactions
  setupCommentReactions();
});

function setupPostReactions() {
  // Target all reaction buttons
  const reactionButtons = document.querySelectorAll('.btn-reaction');
  
  reactionButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      e.preventDefault();
      
      const postId = this.getAttribute('data-post');
      const reactionType = this.getAttribute('data-reaction');
      
      // Use the exact URL from the hx-post attribute
      const url = this.getAttribute('hx-post') || `/post/${postId}/react/`;
      const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
      
      // Send reaction via fetch API
      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': csrfToken,
        },
        body: `reaction_type=${reactionType}`
      })
      .then(response => response.json())
      .then(data => {
        if (data.status === 'success') {
          // Update reaction count display
          const reactionsCount = document.querySelector(`.reactions-count[data-post-id="${postId}"]`);
          if (reactionsCount) {
            if (data.count > 0) {
              reactionsCount.innerHTML = `
                <span class="reactions-badge">
                  <i class="fas fa-thumbs-up text-primary"></i>
                  <span class="ms-1">${data.count}</span>
                </span>
              `;
              reactionsCount.style.display = 'block';
            } else {
              reactionsCount.innerHTML = '';
            }
          }
          
          // Toggle active class on the reaction button
          const mainReactionBtn = button.closest('.reaction-btn-group').querySelector('.reaction-btn');
          if (data.action === 'added' || data.action === 'updated') {
            mainReactionBtn.classList.add('active');
            mainReactionBtn.innerHTML = `<i class="fas fa-thumbs-up me-1 text-primary"></i> ${reactionType.charAt(0).toUpperCase() + reactionType.slice(1)}`;
          } else if (data.action === 'removed') {
            mainReactionBtn.classList.remove('active');
            mainReactionBtn.innerHTML = `<i class="far fa-thumbs-up me-1"></i> Like`;
          }
          
          // Add floating animation
          createHeartAnimation(this);
        }
      })
      .catch(error => console.error('Error:', error));
    });
  });
}

function setupCommentSubmission() {
  // Target all comment forms
  const commentForms = document.querySelectorAll('.comment-form');
  
  commentForms.forEach(form => {
    form.addEventListener('submit', function(e) {
      e.preventDefault();
      
      const postId = this.getAttribute('data-post-id');
      // Use the exact URL from the hx-post attribute
      const url = this.getAttribute('hx-post') || `/post/${postId}/comment/`;
      const formData = new FormData(this);
      const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
      
      // Get the input value to prevent sending empty comments
      const inputElement = this.querySelector('input[name="content"]');
      if (!inputElement || !inputElement.value.trim()) {
        return; // Don't submit empty comments
      }
      
      // Clear the input field immediately for better UX
      const commentText = inputElement.value.trim();
      inputElement.value = '';
      
      // Send comment to server
      fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
        },
        body: formData
      })
      .then(response => response.json())
      .then(data => {
        if (data.status === 'success') {
          // Trigger the HTMX refresh manually
          const commentsList = document.querySelector(`#commentsList-${postId}`);
          if (commentsList && commentsList.getAttribute('hx-get')) {
            // Dispatch an event to trigger HTMX
            const event = new Event('htmx:load');
            commentsList.dispatchEvent(event);
            
            // Manually load fresh data via HTMX
            htmx.trigger(commentsList, 'get');
            
            // Update the comment count
            const count = data.count || 0;
            updateCommentCountDisplay(postId, count);
          }
        }
      })
      .catch(error => {
        console.error('Error:', error);
      });
    });
  });
}

function updateCommentCountDisplay(postId, count) {
  // Update the comment count text if it exists
  const commentsCount = document.querySelector(`.comments-count[data-post-id="${postId}"]`);
  if (commentsCount) {
    // Apply a subtle animation to highlight the count change
    commentsCount.classList.add('count-update-animation');
    commentsCount.textContent = `${count} comment${count !== 1 ? 's' : ''}`;
    commentsCount.style.display = 'inline';
    
    // Remove animation class after animation completes
    setTimeout(() => {
      commentsCount.classList.remove('count-update-animation');
    }, 600);
  } else {
    // Create comments count element if it doesn't exist
    const countContainer = document.querySelector(`.comments-shares-count`);
    if (countContainer) {
      const newCountSpan = document.createElement('span');
      newCountSpan.className = 'small text-muted me-2 comments-count count-update-animation';
      newCountSpan.setAttribute('data-post-id', postId);
      newCountSpan.textContent = `${count} comment${count !== 1 ? 's' : ''}`;
      countContainer.prepend(newCountSpan);
      
      // Remove animation class after animation completes
      setTimeout(() => {
        newCountSpan.classList.remove('count-update-animation');
      }, 600);
    }
  }
}

function setupCommentReactions() {
  // Use event delegation for comment reactions (including dynamically added ones)
  document.addEventListener('click', function(e) {
    const button = e.target.closest('.comment-reaction-btn');
    if (button) {
      e.preventDefault();
      
      const commentId = button.getAttribute('data-comment-id');
      // Use the exact URL from the hx-post attribute
      const url = button.getAttribute('hx-post') || `/comment/${commentId}/react/`;
      const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
      
      // Send reaction via fetch API
      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': csrfToken,
        },
        body: 'reaction_type=like'
      })
      .then(response => response.json())
      .then(data => {
        if (data.status === 'success') {
          // Update reaction count
          const countElement = button.querySelector('.reaction-count');
          if (countElement) {
            countElement.textContent = data.count;
          }
          
          // Toggle active class
          if (data.action === 'added') {
            button.classList.add('active');
            button.querySelector('i').classList.replace('far', 'fas');
          } else if (data.action === 'removed') {
            button.classList.remove('active');
            button.querySelector('i').classList.replace('fas', 'far');
          }
          
          // Add heart animation
          createHeartAnimation(button);
        }
      })
      .catch(error => console.error('Error:', error));
    }
  });
}

function createHeartAnimation(element) {
  // Create floating heart animation
  const heart = document.createElement('div');
  heart.innerHTML = '❤️';
  heart.style.cssText = `
    position: absolute;
    font-size: 1.2rem;
    left: 50%;
    top: 0;
    transform: translateX(-50%);
    pointer-events: none;
    z-index: 100;
    animation: float-up 0.8s forwards ease-out;
  `;
  
  // Set relative position on parent if not already set
  const computedStyle = window.getComputedStyle(element);
  if (computedStyle.position === 'static') {
    element.style.position = 'relative';
  }
  
  // Add heart to element
  element.appendChild(heart);
  
  // Remove after animation completes
  setTimeout(() => heart.remove(), 800);
  
  // Add animation keyframes if not already added
  if (!document.querySelector('style#heart-animation')) {
    const style = document.createElement('style');
    style.id = 'heart-animation';
    style.textContent = `
      @keyframes float-up {
        0% { transform: translate(-50%, 0); opacity: 1; }
        100% { transform: translate(-50%, -20px); opacity: 0; }
      }
      
      @keyframes count-update {
        0% { transform: scale(1); }
        50% { transform: scale(1.2); color: var(--ig-primary); }
        100% { transform: scale(1); }
      }
      
      .count-update-animation {
        animation: count-update 0.6s ease;
      }
    `;
    document.head.appendChild(style);
  }
} 