function updateCountdowns() {
  const countdownElements = document.querySelectorAll('.countdown');
  
  countdownElements.forEach(el => {
    const deadline = el.getAttribute('data-deadline');
    if (!deadline) return;
    
    const deadlineTime = new Date(deadline).getTime();
    const now = new Date().getTime();
    const timeLeft = deadlineTime - now;
    
    if (timeLeft > 0) {
      const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((timeLeft % (1000 * 60)) / 1000);
      el.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
      
      if (timeLeft < 120000) { 
        el.style.animation = 'countdownUrgent 0.5s ease-in-out infinite';
        el.style.color = '#ef4444';
      }
    } else {
      el.textContent = 'Expired';
      el.style.color = '#ef4444';
      el.style.animation = 'none';
      
      setTimeout(() => {
        window.location.reload();
      }, 2000);
    }
  });
}

const urgentStyle = document.createElement('style');
urgentStyle.textContent = `
  @keyframes countdownUrgent {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.1); filter: brightness(1.2); }
  }
`;
document.head.appendChild(urgentStyle);

if (document.querySelectorAll('.countdown').length > 0) {
  updateCountdowns();
  setInterval(updateCountdowns, 1000);
}

document.addEventListener('DOMContentLoaded', function() {
  
  const cards = document.querySelectorAll('.card');
  cards.forEach((card, index) => {
    card.style.animationDelay = `${index * 0.1}s`;
  });
  
  const listItems = document.querySelectorAll('.list li');
  listItems.forEach((item, index) => {
    item.style.animationDelay = `${index * 0.1}s`;
  });
  
  const tableRows = document.querySelectorAll('.table tbody tr');
  tableRows.forEach((row, index) => {
    row.style.animationDelay = `${index * 0.05}s`;
  });
  
  const buttons = document.querySelectorAll('.btn');
  buttons.forEach(btn => {
    btn.addEventListener('click', function(e) {
      const ripple = document.createElement('span');
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const x = e.clientX - rect.left - size / 2;
      const y = e.clientY - rect.top - size / 2;
      
      ripple.style.cssText = `
        position: absolute;
        width: ${size}px;
        height: ${size}px;
        left: ${x}px;
        top: ${y}px;
        background: rgba(255, 255, 255, 0.3);
        border-radius: 50%;
        transform: scale(0);
        animation: ripple 0.6s ease-out;
        pointer-events: none;
      `;
      
      const rippleStyle = document.createElement('style');
      rippleStyle.textContent = `
        @keyframes ripple {
          to {
            transform: scale(2);
            opacity: 0;
          }
        }
      `;
      document.head.appendChild(rippleStyle);
      
      this.appendChild(ripple);
      setTimeout(() => ripple.remove(), 600);
    });
    
    if (btn.type === 'submit' && !btn.closest('form').action.includes('/login')) {
      const form = btn.closest('form');
      if (form) {
        form.addEventListener('submit', function(e) {
          const originalText = btn.innerHTML;
          
          setTimeout(() => {
            btn.innerHTML = `
              <span style="display: inline-flex; align-items: center; gap: 8px;">
                <span class="loading-spinner"></span>
                Processing...
              </span>
            `;
            btn.disabled = true;
            
            if (!document.getElementById('spinner-styles')) {
              const spinnerStyle = document.createElement('style');
              spinnerStyle.id = 'spinner-styles';
              spinnerStyle.textContent = `
                .loading-spinner {
                  width: 16px;
                  height: 16px;
                  border: 2px solid rgba(255, 255, 255, 0.3);
                  border-top: 2px solid white;
                  border-radius: 50%;
                  animation: spin 1s linear infinite;
                }
                @keyframes spin {
                  0% { transform: rotate(0deg); }
                  100% { transform: rotate(360deg); }
                }
              `;
              document.head.appendChild(spinnerStyle);
            }
          }, 10);
        });
      }
    }
  });
  
  const inputs = document.querySelectorAll('.input, textarea, select');
  inputs.forEach(input => {
    input.addEventListener('focus', function() {
      this.parentElement.classList.add('focused');
    });
    
    input.addEventListener('blur', function() {
      this.parentElement.classList.remove('focused');
      if (this.value) {
        this.parentElement.classList.add('filled');
      } else {
        this.parentElement.classList.remove('filled');
      }
    });
    
    input.addEventListener('invalid', function() {
      this.style.borderColor = '#ef4444';
      this.style.boxShadow = '0 0 0 3px rgba(239, 68, 68, 0.3)';
    });
    
    input.addEventListener('input', function() {
      if (this.checkValidity()) {
        this.style.borderColor = 'rgba(255, 255, 255, 0.2)';
        this.style.boxShadow = 'none';
      }
    });
  });
  
  const mediaElements = document.querySelectorAll('.media-strip img, .media-strip video');
  mediaElements.forEach((media, index) => {
    media.style.animationDelay = `${index * 0.1}s`;
    
    media.addEventListener('click', function() {
      showMediaModal(this.src, this.tagName.toLowerCase());
    });
    
    if (media.tagName.toLowerCase() === 'img') {
      media.style.transition = 'filter 0.3s ease';
      
      media.addEventListener('load', function() {
        this.style.filter = 'none';
      });
    }
  });
  
  const flashMessages = document.querySelectorAll('.grid .card[role="alert"]');
  flashMessages.forEach(msg => {
    setTimeout(() => {
      if (msg.parentElement) {
        msg.style.animation = 'slideOutUp 0.5s ease-out forwards';
        setTimeout(() => msg.remove(), 500);
      }
    }, 4000);
  });
  
  const anchorLinks = document.querySelectorAll('a[href^="#"]');
  anchorLinks.forEach(link => {
    link.addEventListener('click', function(e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        target.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  });
  
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };
  
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.animation = 'fadeInUp 0.6s ease-out forwards';
      }
    });
  }, observerOptions);
  
  const animatedElements = document.querySelectorAll('.card, .table, .list');
  animatedElements.forEach(el => {
    observer.observe(el);
  });
});

function showMediaModal(src, type) {
  const modal = document.createElement('div');
  modal.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.9);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
    backdrop-filter: blur(10px);
    animation: fadeIn 0.3s ease-out;
  `;
  
  const mediaEl = document.createElement(type);
  mediaEl.src = src;
  mediaEl.style.cssText = `
    max-width: 90%;
    max-height: 90%;
    border-radius: 12px;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
    animation: scaleIn 0.3s ease-out;
  `;
  
  if (type === 'video') {
    mediaEl.controls = true;
    mediaEl.autoplay = true;
  }
  
  const scaleStyle = document.createElement('style');
  scaleStyle.textContent = `
    @keyframes scaleIn {
      from { transform: scale(0.8); opacity: 0; }
      to { transform: scale(1); opacity: 1; }
    }
  `;
  document.head.appendChild(scaleStyle);
  
  modal.addEventListener('click', function(e) {
    if (e.target === modal) {
      modal.style.animation = 'fadeOut 0.3s ease-out forwards';
      setTimeout(() => modal.remove(), 300);
    }
  });
  
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && document.body.contains(modal)) {
      modal.style.animation = 'fadeOut 0.3s ease-out forwards';
      setTimeout(() => modal.remove(), 300);
    }
  });
  
  modal.appendChild(mediaEl);
  document.body.appendChild(modal);
  
  const fadeOutStyle = document.createElement('style');
  fadeOutStyle.textContent = `
    @keyframes fadeOut {
      from { opacity: 1; }
      to { opacity: 0; }
    }
  `;
  document.head.appendChild(fadeOutStyle);
}

function enhanceTableInteractions() {
  const tables = document.querySelectorAll('.table');
  tables.forEach(table => {
    const headers = table.querySelectorAll('th');
    headers.forEach((header, index) => {
      header.style.cursor = 'pointer';
      header.addEventListener('click', function() {
        this.style.background = 'rgba(255, 255, 255, 0.2)';
        setTimeout(() => {
          this.style.background = 'rgba(255, 255, 255, 0.1)';
        }, 200);
      });
    });
    
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
      row.addEventListener('mouseenter', function() {
        this.style.transform = 'scale(1.02)';
        this.style.zIndex = '10';
      });
      
      row.addEventListener('mouseleave', function() {
        this.style.transform = 'scale(1)';
        this.style.zIndex = 'auto';
      });
    });
  });
}

function addParallaxEffect() {
  let scrolled = 0;
  
  window.addEventListener('scroll', function() {
    scrolled = window.pageYOffset;
    const parallax = document.body;
    const speed = scrolled * 0.5;
    
    parallax.style.backgroundPosition = `center ${speed}px`;
  });
}

function addTypingAnimation() {
  const headings = document.querySelectorAll('h1, h2');
  
  headings.forEach(heading => {
    const text = heading.textContent;
    heading.textContent = '';
    heading.style.borderRight = '2px solid rgba(255, 255, 255, 0.7)';
    heading.style.animation = 'blink 1s infinite';
    
    let i = 0;
    const typeWriter = setInterval(() => {
      if (i < text.length) {
        heading.textContent += text.charAt(i);
        i++;
      } else {
        clearInterval(typeWriter);
        setTimeout(() => {
          heading.style.borderRight = 'none';
          heading.style.animation = 'none';
        }, 1000);
      }
    }, 100);
  });
  
  const blinkStyle = document.createElement('style');
  blinkStyle.textContent = `
    @keyframes blink {
      0%, 50% { border-color: rgba(255, 255, 255, 0.7); }
      51%, 100% { border-color: transparent; }
    }
  `;
  document.head.appendChild(blinkStyle);
}

function addParticleEffect() {
  const canvas = document.createElement('canvas');
  canvas.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: -1;
    pointer-events: none;
  `;
  
  document.body.appendChild(canvas);
  
  const ctx = canvas.getContext('2d');
  let particles = [];
  
  function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  
  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();
  
  for (let i = 0; i < 50; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      size: Math.random() * 3 + 1,
      speedX: Math.random() * 2 - 1,
      speedY: Math.random() * 2 - 1,
      opacity: Math.random() * 0.5 + 0.2
    });
  }
  
  function animateParticles() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    particles.forEach(particle => {
      particle.x += particle.speedX;
      particle.y += particle.speedY;
      
      if (particle.x > canvas.width) particle.x = 0;
      if (particle.x < 0) particle.x = canvas.width;
      if (particle.y > canvas.height) particle.y = 0;
      if (particle.y < 0) particle.y = canvas.height;
      
      ctx.beginPath();
      ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255, 255, 255, ${particle.opacity})`;
      ctx.fill();
    });
    
    requestAnimationFrame(animateParticles);
  }
  
  animateParticles();
}

document.addEventListener('DOMContentLoaded', function() {
  enhanceTableInteractions();
  addParallaxEffect();
  addParticleEffect();
  
  setTimeout(addTypingAnimation, 500);
  
  document.body.style.opacity = '0';
  document.body.style.transition = 'opacity 0.5s ease-in';
  
  window.addEventListener('load', function() {
    document.body.style.opacity = '1';
  });
});

let touchStartX = 0;
let touchEndX = 0;

document.addEventListener('touchstart', function(e) {
  touchStartX = e.changedTouches[0].screenX;
});

document.addEventListener('touchend', function(e) {
  touchEndX = e.changedTouches[0].screenX;
  handleSwipe();
});

function handleSwipe() {
  const swipeThreshold = 50;
  const diff = touchStartX - touchEndX;
  
  if (Math.abs(diff) > swipeThreshold) {
    if (diff > 0) {
      console.log('Swiped left');
    } else {
      console.log('Swiped right');
    }
  }
}

let konamiCode = [];
const konamiSequence = [
  'ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown',
  'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight',
  'KeyB', 'KeyA'
];

document.addEventListener('keydown', function(e) {
  konamiCode.push(e.code);
  
  if (konamiCode.length > konamiSequence.length) {
    konamiCode.shift();
  }
  
  if (konamiCode.join(',') === konamiSequence.join(',')) {
    document.body.style.animation = 'bluePulse 2s ease-in-out 3 times';
    
    const pulseStyle = document.createElement('style');
    pulseStyle.textContent = `
      @keyframes bluePulse {
        0%, 100% { filter: brightness(1); }
        50% { filter: brightness(1.2) saturate(1.3); }
      }
    `;
    document.head.appendChild(pulseStyle);
    
    setTimeout(() => {
      document.body.style.animation = 'none';
    }, 6000);
    
    konamiCode = [];
  }
});

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

window.addEventListener('scroll', debounce(function() {
}, 16));

console.log('🎨 Modern UI loaded with animations and interactions!');