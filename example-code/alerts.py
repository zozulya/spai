"""
Alert Management System

Sends alerts via email, Telegram, or console based on configuration.
Includes cooldown to prevent spam.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
import json


class AlertManager:
    """Manages alerting with cooldown logic"""
    
    def __init__(self, config: Dict, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.alerts_config = config.get('alerts', {})
        self.enabled = self.alerts_config.get('enabled', False)
        
        # Cooldown tracking
        self.cooldown_file = Path('output/logs/alert_cooldown.json')
        self.cooldown_hours = 6  # Don't send same alert within 6 hours
        self.cooldowns = self._load_cooldowns()
    
    def _load_cooldowns(self) -> Dict:
        """Load alert cooldown timestamps"""
        if not self.cooldown_file.exists():
            return {}
        
        try:
            with open(self.cooldown_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_cooldowns(self):
        """Save cooldown timestamps"""
        self.cooldown_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cooldown_file, 'w') as f:
            json.dump(self.cooldowns, f, indent=2)
    
    def _check_cooldown(self, alert_key: str) -> bool:
        """Check if alert is in cooldown period"""
        if alert_key not in self.cooldowns:
            return False
        
        last_sent = datetime.fromisoformat(self.cooldowns[alert_key])
        cooldown_until = last_sent + timedelta(hours=self.cooldown_hours)
        
        return datetime.utcnow() < cooldown_until
    
    def _update_cooldown(self, alert_key: str):
        """Update cooldown timestamp for alert"""
        self.cooldowns[alert_key] = datetime.utcnow().isoformat()
        self._save_cooldowns()
    
    def send_critical(self, message: str, context: Optional[Dict] = None):
        """Send critical alert (always sent, bypass cooldown for criticals)"""
        self.logger.critical(message, extra=context or {})
        
        if not self.enabled:
            return
        
        self._send_email(
            subject=f"🚨 CRITICAL: AutoSpanishBlog - {message}",
            body=self._format_alert_body(message, context, 'CRITICAL'),
            priority='high'
        )
    
    def send_error(self, message: str, context: Optional[Dict] = None):
        """Send error alert (respects cooldown)"""
        alert_key = f"error:{message[:50]}"
        
        self.logger.error(message, extra=context or {})
        
        if not self.enabled or self._check_cooldown(alert_key):
            return
        
        self._send_email(
            subject=f"❌ ERROR: AutoSpanishBlog - {message}",
            body=self._format_alert_body(message, context, 'ERROR')
        )
        
        self._update_cooldown(alert_key)
    
    def send_warning(self, message: str, context: Optional[Dict] = None):
        """Send warning alert (respects cooldown)"""
        alert_key = f"warning:{message[:50]}"
        
        self.logger.warning(message, extra=context or {})
        
        if not self.enabled or self._check_cooldown(alert_key):
            return
        
        # Warnings go to daily digest (not implemented yet)
        # For now, just log
        pass
    
    def _format_alert_body(self, message: str, context: Optional[Dict], severity: str) -> str:
        """Format alert email body"""
        body = f"""AutoSpanishBlog Alert
        
Severity: {severity}
Time: {datetime.utcnow().isoformat()}Z
Message: {message}

"""
        
        if context:
            body += "Context:\n"
            for key, value in context.items():
                body += f"  {key}: {value}\n"
        
        body += "\n---\nAutoSpanishBlog Alert System"
        
        return body
    
    def _send_email(self, subject: str, body: str, priority: str = 'normal'):
        """Send email alert"""
        email_config = self.alerts_config.get('email_config', {})
        to_email = self.alerts_config.get('email')
        
        if not to_email:
            self.logger.warning("Alert email not configured, skipping email send")
            return
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = email_config.get('from', 'bot@autospanish.com')
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if priority == 'high':
                msg['X-Priority'] = '1'
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send via SMTP
            smtp_config = email_config.get('smtp', {})
            server = smtplib.SMTP(
                smtp_config.get('host', 'smtp.gmail.com'),
                smtp_config.get('port', 587)
            )
            server.starttls()
            
            username = smtp_config.get('username')
            password = smtp_config.get('password')
            
            if username and password:
                server.login(username, password)
            
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Alert email sent: {subject}")
        
        except Exception as e:
            self.logger.error(f"Failed to send alert email: {e}")
    
    def send_telegram(self, message: str):
        """Send Telegram alert (optional)"""
        telegram_config = self.alerts_config.get('telegram', {})
        
        if not telegram_config.get('enabled', False):
            return
        
        bot_token = telegram_config.get('bot_token')
        chat_id = telegram_config.get('chat_id')
        
        if not bot_token or not chat_id:
            return
        
        try:
            import requests
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            
            self.logger.info("Telegram alert sent")
        
        except Exception as e:
            self.logger.error(f"Failed to send Telegram alert: {e}")
