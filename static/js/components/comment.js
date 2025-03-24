// Comment Component Animations
document.addEventListener('DOMContentLoaded', function() {
  // Add animations to comments
  const animateComments = function() {
    const comments = document.querySelectorAll('.comment');
    
    comments.forEach(function(comment, index) {
      // Add staggered fade in
      comment.style.opacity = '0';
      comment.style.transform = 'translateY(10px)';
      
      setTimeout(function() {
        comment.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        comment.style.opacity = '1';
        comment.style.transform = 'translateY(0)';
      }, 100 + (index * 50));
      
      // Add hover effect
      comment.addEventListener('mouseenter', function() {
        const commentContent = this.querySelector('.comment-content');
        if (commentContent) {
          commentContent.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.1)';
          commentContent.style.transform = 'translateY(-2px)';
          commentContent.style.transition = 'all 0.3s ease';
        }
      });
      
      comment.addEventListener('mouseleave', function() {
        const commentContent = this.querySelector('.comment-content');
        if (commentContent) {
          commentContent.style.boxShadow = '';
          commentContent.style.transform = '';
        }
      });
    });
  };
  
  // Add animation to like/reply buttons
  const enhanceButtons = function() {
    // Comment action buttons
    const actionButtons = document.querySelectorAll('.comment-actions .btn');
    
    actionButtons.forEach(function(btn) {
      btn.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-2px)';
        this.style.transition = 'all 0.2s ease';
      });
      
      btn.addEventListener('mouseleave', function() {
        this.style.transform = '';
      });
      
      // Add heart animation for like button
      if (btn.classList.contains('like-btn') || btn.querySelector('.fa-heart')) {
        btn.addEventListener('click', function() {
          // Add heart animation
          const heart = document.createElement('span');
          heart.innerHTML = '❤️';
          heart.style.cssText = `
            position: absolute;
            font-size: 1rem;
            left: 50%;
            top: 0;
            pointer-events: none;
            animation: float-up 0.8s forwards ease-out;
          `;
          
          this.style.position = 'relative';
          this.appendChild(heart);
          
          setTimeout(function() {
            heart.remove();
          }, 800);
        });
      }
      
      // Add toggle animation for reply form
      if (btn.classList.contains('reply-btn') || btn.textContent.includes('Reply')) {
        btn.addEventListener('click', function() {
          const commentId = this.closest('.comment').getAttribute('data-comment-id');
          const replyForm = document.querySelector(`.reply-form[data-parent="${commentId}"]`);
          
          if (replyForm) {
            if (replyForm.style.display === 'none' || !replyForm.style.display) {
              replyForm.style.display = 'block';
              replyForm.style.opacity = '0';
              replyForm.style.transform = 'translateY(10px)';
              
              setTimeout(function() {
                replyForm.style.transition = 'all 0.3s ease';
                replyForm.style.opacity = '1';
                replyForm.style.transform = 'translateY(0)';
                
                // Focus on textarea
                const textarea = replyForm.querySelector('textarea');
                if (textarea) {
                  textarea.focus();
                }
              }, 10);
            } else {
              replyForm.style.opacity = '0';
              replyForm.style.transform = 'translateY(10px)';
              
              setTimeout(function() {
                replyForm.style.display = 'none';
              }, 300);
            }
          }
        });
      }
    });
  };
  
  // Enhance comment submission
  const enhanceCommentForm = function() {
    const commentForms = document.querySelectorAll('.comment-form, .reply-form');
    
    commentForms.forEach(function(form) {
      // Add animation to textarea
      const textarea = form.querySelector('textarea');
      if (textarea) {
        textarea.addEventListener('focus', function() {
          this.style.transition = 'all 0.3s ease';
          this.style.transform = 'translateY(-2px)';
          this.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.1)';
        });
        
        textarea.addEventListener('blur', function() {
          this.style.transform = '';
          this.style.boxShadow = '';
        });
      }
      
      // Add animation to submit button
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) {
        submitBtn.addEventListener('mouseenter', function() {
          this.style.transform = 'translateY(-2px)';
          this.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.1)';
          this.style.transition = 'all 0.2s ease';
        });
        
        submitBtn.addEventListener('mouseleave', function() {
          this.style.transform = '';
          this.style.boxShadow = '';
        });
        
        // Add submission animation
        form.addEventListener('submit', function() {
          // Show loading spinner
          if (submitBtn.innerHTML.indexOf('fa-spinner') === -1) {
            submitBtn.originalHTML = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            
            // Reset button after delay (in a real app this would be after AJAX completes)
            setTimeout(function() {
              submitBtn.innerHTML = '<i class="fas fa-check"></i>';
              
              setTimeout(function() {
                submitBtn.innerHTML = submitBtn.originalHTML;
              }, 1000);
            }, 800);
          }
        });
      }
    });
  };
  
  // Add animations for comment deletion
  const enhanceDeleteButtons = function() {
    const deleteButtons = document.querySelectorAll('.delete-comment');
    
    deleteButtons.forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        // Get the parent comment
        const comment = this.closest('.comment');
        if (!comment) return;
        
        // Add fade out animation
        comment.style.transition = 'all 0.5s ease';
        comment.style.opacity = '0';
        comment.style.transform = 'translateY(20px)';
        comment.style.height = comment.offsetHeight + 'px';
        
        setTimeout(function() {
          comment.style.height = '0px';
          comment.style.marginBottom = '0px';
          comment.style.paddingTop = '0px';
          comment.style.paddingBottom = '0px';
          
          // In a real app, this would be after confirmation and AJAX delete
          setTimeout(function() {
            comment.remove();
          }, 300);
        }, 300);
      });
    });
  };
  
  // Run only if comment elements exist
  if (document.querySelectorAll('.comment').length > 0) {
    animateComments();
    enhanceButtons();
    enhanceCommentForm();
    enhanceDeleteButtons();
    
    // Add animation styles
    if (!document.querySelector('style#comment-styles')) {
      const style = document.createElement('style');
      style.id = 'comment-styles';
      style.textContent = `
        @keyframes float-up {
          0% { transform: translate(-50%, 0); opacity: 1; }
          100% { transform: translate(-50%, -20px); opacity: 0; }
        }
        
        .comment {
          transition: all 0.3s ease;
        }
        
        .comment-content {
          transition: all 0.3s ease;
        }
        
        .comment-actions .btn {
          position: relative;
          transition: all 0.2s ease;
        }
        
        .reply-form {
          transition: all 0.3s ease;
        }
      `;
      document.head.appendChild(style);
    }
  }
});