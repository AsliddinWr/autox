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
    
    <script
