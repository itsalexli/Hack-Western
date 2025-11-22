# Backend Setup

## ElevenLabs API Configuration

To use the ElevenLabs API, you need to set up your API key:

### Step 1: Get Your API Key

1. Go to [ElevenLabs Settings](https://elevenlabs.io/app/settings/api-keys)
2. Sign in or create an account
3. Copy your API key

### Step 2: Configure the API Key

**Option 1: Using Environment Variable (Recommended)**

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` and replace `your_api_key_here` with your actual API key:
   ```
   ELEVENLABS_API_KEY=sk_your_actual_api_key_here
   ```

**Option 2: Directly in Code (Not Recommended for Production)**
Edit `elevenLabs.py` and replace:

```python
client = ElevenLabs(
    api_key=os.environ.get("ELEVENLABS_API_KEY")
)
```

with:

```python
client = ElevenLabs(
    api_key="sk_your_actual_api_key_here"
)
```

### Step 3: Install Dependencies

```bash
pip install elevenlabs python-dotenv
```

### Step 4: Load Environment Variables

Add this to the top of `elevenLabs.py`:

```python
from dotenv import load_dotenv
load_dotenv()
```

## Important Notes

- **Never commit your `.env` file** - it's already in `.gitignore`
- Keep your API key secret
- The API key should start with `sk_` or similar prefix
