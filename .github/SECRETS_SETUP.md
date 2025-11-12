# GitHub Secrets Setup

To enable automated article generation, you need to configure the following secrets in your GitHub repository.

## Required Secrets

### 1. LLM API Keys

Go to: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

#### OPENAI_API_KEY
- **Name:** `OPENAI_API_KEY`
- **Value:** Your OpenAI API key (starts with `sk-proj-...`)
- **Used for:** Article generation (GPT-4o) and quality checking (GPT-4o-mini)

#### ANTHROPIC_API_KEY (Optional)
- **Name:** `ANTHROPIC_API_KEY`
- **Value:** Your Anthropic API key (starts with `sk-ant-...`)
- **Used for:** Fallback LLM provider if needed

### 2. Email Notifications (Optional)

These are used to send failure alerts. If you don't set these up, the workflow will still run but won't send email notifications.

#### EMAIL_USERNAME
- **Name:** `EMAIL_USERNAME`
- **Value:** Your Gmail address (e.g., `your.email@gmail.com`)

#### EMAIL_PASSWORD
- **Name:** `EMAIL_PASSWORD`
- **Value:** Gmail App Password (NOT your regular password)
- **How to get:**
  1. Go to https://myaccount.google.com/apppasswords
  2. Create a new app password for "Mail"
  3. Copy the 16-character password
  4. Use this as the secret value

#### ALERT_EMAIL
- **Name:** `ALERT_EMAIL`
- **Value:** Email address to receive alerts (can be same as EMAIL_USERNAME)

## Verification

After setting up secrets, you can verify they're configured by:

1. Going to **Actions** tab
2. Selecting **Generate Spanish Learning Articles** workflow
3. Clicking **Run workflow** (manual trigger)
4. Checking the workflow runs successfully

## Security Notes

- Never commit API keys to git
- Rotate API keys every 90 days
- Use separate API keys for production vs development
- Monitor API usage through provider dashboards

## Cost Monitoring

- OpenAI: https://platform.openai.com/usage
- Anthropic: https://console.anthropic.com/settings/usage

Expected monthly cost: ~$10-12 for 360 articles/month (12/day)
