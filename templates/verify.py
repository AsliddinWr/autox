<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kodni tasdiqlash - Telegram Auto Poster</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <div class="verify-box">
            <div class="back-button" onclick="window.location.href='/login'">
                ← Orqaga
            </div>
            
            <div class="verify-icon">
                <svg width="60" height="60" viewBox="0 0 48 48" fill="none">
                    <circle cx="24" cy="24" r="24" fill="#0088cc" opacity="0.1"/>
                    <rect x="16" y="16" width="16" height="16" rx="3" stroke="#0088cc" stroke-width="2"/>
                    <path d="M20 24L22.5 26.5L28 21" stroke="#0088cc" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </div>
            
            <h2>Tasdiqlash kodi</h2>
            <p class="subtitle">Telegram akkauntingizga yuborilgan 5 xonali kodni kiriting</p>
            
            <form id="verifyForm">
                <div class="code-input-group">
                    <input type="text" class="code-input" maxlength="1" pattern="[0-9]" inputmode="numeric" autocomplete="off">
                    <input type="text" class="code-input" maxlength="1" pattern="[0-9]" inputmode="numeric" autocomplete="off">
                    <input type="text" class="code-input" maxlength="1" pattern="[0-9]" inputmode="numeric" autocomplete="off">
                    <input type="text" class="code-input" maxlength="1" pattern="[0-9]" inputmode="numeric" autocomplete="off">
                    <input type="text" class="code-input" maxlength="1" pattern="[0-9]" inputmode="numeric" autocomplete="off">
                </div>
                
                <input type="hidden" id="codeValue" name="code">
                
                <button type="submit" class="btn-primary" id="submitBtn">
                    <span class="btn-text">Tasdiqlash</span>
                    <span class="spinner" style="display: none;">
                        <div class="dot-spinner"></div>
                    </span>
                </button>
                
                <div class="error-message" id="errorMessage" style="display: none;"></div>
            </form>
            
            <div class="resend-section">
                <p>Kod kelmadimi?</p>
                <button class="btn-resend" onclick="resendCode()" id="resendBtn">
                    Qayta yuborish (<span id="timer">60</span>s)
                </button>
            </div>
        </div>
    </div>
    
    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        tg.ready();
        
        const inputs = document.querySelectorAll('.code-input');
        
        // Inputlarni boshqarish
        inputs.forEach((input, index) => {
            input.addEventListener('input', (e) => {
                const value = e.target.value;
                
                // Faqat raqam kiritish
                if (!/^\d*$/.test(value)) {
                    e.target.value = '';
                    return;
                }
                
                if (value.length === 1 && index < inputs.length - 1) {
                    inputs[index + 1].focus();
                }
                
                updateCodeValue();
            });
            
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Backspace' && !input.value && index > 0) {
                    inputs[index - 1].focus();
                }
                
                // Paste hodisasi
                if (e.key === 'v' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    navigator.clipboard.readText().then(text => {
                        const code = text.replace(/\D/g, '').slice(0, 5);
                        for (let i = 0; i < inputs.length; i++) {
                            inputs[i].value = code[i] || '';
                        }
                        updateCodeValue();
                        if (code.length === 5) {
                            inputs[4].focus();
                        }
                    });
                }
            });
        });
        
        function updateCodeValue() {
            const code = Array.from(inputs).map(input => input.value).join('');
            document.getElementById('codeValue').value = code;
        }
        
        // Formani yuborish
        document.getElementById('verifyForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const code = document.getElementById('codeValue').value;
            const submitBtn = document.getElementById('submitBtn');
            const errorMessage = document.getElementById('errorMessage');
            
            if (code.length !== 5) {
                errorMessage.textContent = 'Iltimos, 5 xonali kodni to\'liq kiriting';
                errorMessage.style.display = 'block';
                return;
            }
            
            submitBtn.disabled = true;
            document.querySelector('.btn-text').style.display = 'none';
            document.querySelector('.spinner').style.display = 'block';
            errorMessage.style.display = 'none';
            
            try {
                const response = await fetch('/verify', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: `code=${code}`
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    window.location.href = '/dashboard';
                } else {
                    throw new Error(data.error || 'Xatolik yuz berdi');
                }
            } catch (error) {
                errorMessage.textContent = error.message;
                errorMessage.style.display = 'block';
                
                submitBtn.disabled = false;
                document.querySelector('.btn-text').style.display = 'block';
                document.querySelector('.spinner').style.display = 'none';
            }
        });
        
        // Timer
        let timeLeft = 60;
        const timerElement = document.getElementById('timer');
        const resendBtn = document.getElementById('resendBtn');
        resendBtn.disabled = true;
        
        const countdown = setInterval(() => {
            timeLeft--;
            timerElement.textContent = timeLeft;
            
            if (timeLeft <= 0) {
                clearInterval(countdown);
                resendBtn.disabled = false;
                resendBtn.textContent = 'Qayta yuborish';
            }
        }, 1000);
        
        function resendCode() {
            window.location.href = '/login';
        }
        
        // Birinchi inputga fokus
        inputs[0].focus();
    </script>
</body>
</html>
