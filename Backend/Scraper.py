from bs4 import BeautifulSoup
import re
from flask import Flask, request, Response
from flask_cors import CORS, cross_origin
import traceback
import os
from openai import OpenAI
from typing import Optional


app = Flask(__name__)

# You can restrict origins later; for now allow everything while developing
CORS(app, resources={r"/clean_html": {"origins": "*"}})

MODEL_NAME = "gpt-4.1-mini"

SYSTEM_PROMPT = """
You are an accessibility-focused HTML transformer. Transform webpage main content into clear, accessible layouts for older adults and people with cognitive/visual challenges.

CRITICAL REQUIREMENTS:
1. MUST include "Primary Actions" section (2-4 action chips) - infer if needed
2. NO overlapping content - use proper grid spacing
3. Output EXACTLY ONE <main class="a11y-page" role="main">...</main>
4. DO NOT modify or remove the original page header - it will be preserved automatically
5. Your <main> content should work with ANY header at the top

IMPORTANT - HEADER BEHAVIOR:
- The original site's header/navigation will remain at the top of the page
- Your generated content will appear BELOW the header
- Do NOT add any top margin or positioning to compensate for header height
- The CSS will handle spacing automatically

STRICT OUTPUT REQUIREMENT:
- Return EXACTLY ONE root element:
    <main class="a11y-page" role="main"> … </main>
- No text, comments, or whitespace BEFORE or AFTER this <main> element.

MANDATORY STRUCTURE:
Your output MUST contain these sections in this order:

1. HERO ROW (REQUIRED):
   <section class="a11y-hero-row">
     <article class="a11y-card a11y-overview-card">
       [Overview of what this page is about - 2-4 sentences]
     </article>
     <aside class="a11y-card a11y-actions-card" aria-label="Primary actions">
       <h2>What You Can Do</h2>
       <div class="a11y-actions-layout">
         <div class="a11y-primary-actions">
           [2-4 action chips - ALWAYS include this, even if you need to infer actions]
         </div>
       </div>
     </aside>
   </section>

2. CONTENT SECTION(S) (OPTIONAL but recommended):
   <section class="a11y-content-section">
     <article class="a11y-card a11y-condensed-content">
       [Main content details]
     </article>
   </section>

3. ADDITIONAL INFO (OPTIONAL):
   <section class="a11y-content-grid">
     <article class="a11y-card">
       [Additional details]
     </article>
     <aside class="a11y-card a11y-quick-facts">
       [Quick facts or key points]
     </aside>
   </section>

4. FOOTER (REQUIRED):
   <footer class="a11y-footer">
     <span class="a11y-large-text">
       This view simplifies the main details. Check the full site or speak with
       an advisor if you have questions.
     </span>
     <span class="a11y-large-text">
       Source:&nbsp;
       <a href="[original URL]" target="_blank" rel="noopener noreferrer">
         [Short site name]
       </a>
     </span>
   </footer>

ACTION CHIP REQUIREMENTS:
- Each action chip MUST use this exact structure:
  <a href="[URL]" class="a11y-action-chip">
    <span>[Action Title]</span>
    <span>[Brief description]</span>
  </a>
- If no URLs exist in source, use "#" or the page's main URL
- ALWAYS provide 2-4 action chips, infer from context if needed

EXAMPLES OF ACTIONS TO INFER:
- If it's a product page: "Get a Quote", "Learn More", "Contact Sales", "View Details"
- If it's an informational page: "Read Full Article", "Contact Us", "Get Help", "Find Locations"
- If it's a service page: "Apply Now", "Check Eligibility", "Get Started", "Find an Advisor"
- If it's a contact page: "Send Message", "Call Us", "Find Location", "Get Support"

OVERLAP PREVENTION:
- The CSS grid will handle spacing automatically
- DO NOT add margin-top or positioning that could cause overlaps
- Keep content within the card boundaries
- Each card should be self-contained

FORBIDDEN:
- Empty or missing primary actions section
- Overlapping cards or content
- Content extending outside cards
- Missing the hero row with actions card
- Missing footer

------------------------------
READING LEVEL & CONTENT
------------------------------

Audience:
- Older adults
- People with low vision
- People who get overwhelmed by busy layouts

Language:
- Aim for grade 5–7 reading level
- Sentences 8–16 words long
- Use common, everyday words
- Explain any technical term in one simple sentence

Keep only:
- What the page is about
- Who it is for
- Main actions (buttons/flows)
- Key facts, limits, or warnings
- Simple "next steps"

Include:
- Clear explanations of what the product/service does
- Plain-language explanations of benefits and important conditions
- Enough detail that the reader could make a basic decision or know what to ask

Remove:
- Marketing hype and filler
- Long intros and stories
- Repetition
- Most fine-print legal text (unless absolutely critical to understanding)

Ideal length: about 700–1400 words
Prefer lists and short paragraphs over large text blocks

------------------------------
ACTIONS & LINKS
------------------------------

For CTAs and chips:
- Use <a> elements, not <button>
- Reuse href URLs from important links in the source HTML
- If multiple links go to the same main action, pick one
- If you cannot confidently choose a specific URL, use "#" as placeholder
- NEVER leave the actions section empty - always create 2-4 relevant actions

------------------------------
GENERAL REMINDERS
------------------------------

- Output exactly one <main class="a11y-page" role="main">…</main> element
- No extra text before or after this main element
- Make text large and easy to read by applying class="a11y-large-text"
  to most user-facing paragraphs and list items
- Use <a> tags with href URLs for interactive buttons and chips
- Talk directly to the reader ("you", "we"), and avoid meta "this website" phrasing
- ALWAYS include the primary actions section - this is non-negotiable
- Ensure proper spacing between cards to prevent overlaps
"""

ACCESSIBLE_CSS = r"""
.a11y-page {
  margin: 0 auto 40px;
  max-width: 1200px;
  padding: 0 24px 40px;
  font-size: 1.2rem;
  line-height: 1.8;
  position: relative;
}

@media (max-width: 768px) {
  .a11y-page {
    padding: 0 16px 28px;
    font-size: 1.1rem;
  }
}

.a11y-hero-row,
.a11y-content-grid {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1.5fr);
  gap: 24px;
  margin-bottom: 24px;
  position: relative;
}

@media (max-width: 900px) {
  .a11y-hero-row,
  .a11y-content-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

.a11y-content-section {
  margin-bottom: 24px;
  position: relative;
}

.a11y-card {
  background: rgba(255, 255, 255, 0.98);
  border-radius: 22px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  padding: 24px 24px 20px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
  position: relative;
  z-index: 1;
  overflow: hidden;
}

.a11y-actions-card {
  min-height: 200px;
}

.a11y-actions-card h2 {
  margin-top: 0;
  margin-bottom: 16px;
  font-size: 1.3rem;
}

/* ===================================
   HEADINGS & SUBTITLES - BOLDED
   =================================== */

h1, h2, h3, h4, h5, h6 {
  margin-top: 0;
  margin-bottom: 0.75em;
  font-weight: 700; /* Always bold */
  line-height: 1.3;
}

h1 {
  font-size: clamp(2rem, 3vw, 2.5rem);
}

h2 {
  font-size: clamp(1.5rem, 2.5vw, 2rem);
  font-weight: 700; /* Strong bold for subtitles */
}

h3 {
  font-size: clamp(1.3rem, 2vw, 1.75rem);
  font-weight: 700;
}

h4 {
  font-size: clamp(1.2rem, 1.8vw, 1.5rem);
  font-weight: 700;
}

h5, h6 {
  font-size: clamp(1.1rem, 1.5vw, 1.3rem);
  font-weight: 700;
}

/* ===================================
   BUTTONS - BIG & HIGH CONTRAST
   =================================== */

/* Make anchors with button classes look like actual buttons */
a.a11y-primary-btn,
a.a11y-secondary-btn {
  text-decoration: none;
  color: #FFFFFF;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.1rem;
  padding: 16px 32px;
  min-height: 56px;
  border-radius: 12px;
  border: none;
  cursor: pointer;
  transition: all 200ms ease-out;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.a11y-primary-btn {
  background: #0066CC; /* High contrast blue */
  color: #FFFFFF;
}

.a11y-primary-btn:hover {
  background: #0052A3;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
}

.a11y-primary-btn:active {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.a11y-secondary-btn {
  background: #2D3748; /* High contrast dark gray */
  color: #FFFFFF;
}

.a11y-secondary-btn:hover {
  background: #1A202C;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
}

.a11y-secondary-btn:active {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

/* Top labels / header */

.a11y-section-label {
  font-size: 0.78rem;
  font-weight: 700; /* Bold labels */
  text-transform: uppercase;
  letter-spacing: 0.18em;
  opacity: 0.8;
  margin-bottom: 14px;
}

.a11y-site-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;
}

.a11y-site-id {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.a11y-favicon {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.85);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 1rem;
  flex-shrink: 0;
}

.a11y-site-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.a11y-site-title {
  margin: 0 0 4px;
  font-size: clamp(2.1rem, 2.8vw, 2.5rem);
  font-weight: 700;
  line-height: 1.2;
}

.a11y-site-url {
  margin: 0;
  font-size: 0.95rem;
  opacity: 0.8;
  word-break: break-all;
}

.a11y-pill-badge {
  align-self: flex-start;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.8rem;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: rgba(0, 0, 0, 0.02);
}

.a11y-pill-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: currentColor;
  opacity: 0.7;
}

.a11y-hero-summary {
  margin: 10px 0 16px;
  opacity: 0.9;
}

/* CTA row + buttons */

.a11y-hero-cta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

/* Actions panel */

.a11y-actions-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.a11y-primary-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  position: relative;
}

/* ===================================
   ACTION CHIPS - BIG & HIGH CONTRAST
   =================================== */

.a11y-action-chip {
  text-decoration: none;
  color: #1A202C;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  flex: 1 1 calc(50% - 8px);
  min-width: 200px;
  min-height: 100px; /* Make chips taller */
  max-width: 100%;
  border-radius: 16px;
  padding: 18px 20px; /* Bigger padding */
  border: 3px solid #0066CC; /* Thicker, high-contrast border */
  background: #FFFFFF;
  cursor: pointer;
  text-align: left;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transition: all 200ms ease-out;
  position: relative;
  z-index: 1;
}

@media (max-width: 600px) {
  .a11y-action-chip {
    flex: 1 1 100%;
  }
}

.a11y-action-chip span:first-child {
  font-weight: 700; /* Bold title */
  font-size: 1.2rem; /* Bigger title */
  margin-bottom: 6px;
  display: block;
  color: #0066CC; /* High contrast blue */
}

.a11y-action-chip span:last-child {
  font-size: 1rem; /* Bigger description */
  opacity: 0.9;
  display: block;
  color: #2D3748;
  font-weight: 500; /* Slightly bold description */
}

.a11y-action-chip:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 20px rgba(0, 102, 204, 0.3);
  border-color: #0052A3;
  background: #F7FAFC;
  z-index: 2;
}

.a11y-action-chip:active {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 102, 204, 0.2);
}

/* Meta row */

.a11y-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 0.85rem;
  opacity: 0.8;
}

.a11y-meta-row span {
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.06);
  font-weight: 600;
}

/* Lists */

.a11y-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-left: 0;
  margin: 0;
}

.a11y-list li {
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.95);
  border: 2px solid rgba(0, 0, 0, 0.08);
  font-size: 1.05rem;
}

.a11y-list li strong {
  display: block;
  margin-bottom: 6px;
  font-weight: 700; /* Bold list item titles */
  font-size: 1.1rem;
}

/* Tags */

.a11y-tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.a11y-tag {
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 0.9rem;
  background: rgba(0, 0, 0, 0.06);
  font-weight: 600;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

/* Footer */

.a11y-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  margin-top: 16px;
  border-top: 2px dashed rgba(0, 0, 0, 0.15);
  font-size: 0.95rem;
  opacity: 0.9;
  clear: both;
}

.a11y-footer a {
  text-decoration: underline;
  font-weight: 600;
  color: #0066CC;
}

.a11y-footer a:hover {
  color: #0052A3;
}

/* Text sizing helpers */

.a11y-large-text {
  font-size: 1.15em;
  line-height: 1.6;
}

.a11y-important-text {
  font-weight: 700; /* Bold important text */
  color: #1A202C;
}

/* Ensure paragraphs have proper spacing */
p {
  margin-top: 0;
  margin-bottom: 1em;
  line-height: 1.7;
}

p:last-child {
  margin-bottom: 0;
}

/* Strong and emphasis elements */
strong, b {
  font-weight: 700;
  color: #1A202C;
}

em, i {
  font-style: italic;
  font-weight: 600;
}

/* Links in content */
.a11y-card a:not(.a11y-action-chip):not(.a11y-primary-btn):not(.a11y-secondary-btn) {
  color: #0066CC;
  text-decoration: underline;
  font-weight: 600;
}

.a11y-card a:not(.a11y-action-chip):not(.a11y-primary-btn):not(.a11y-secondary-btn):hover {
  color: #0052A3;
  text-decoration-thickness: 2px;
}
"""

# helper function
def require_api_key() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Run:\n\n"
            "  export OPENAI_API_KEY='your_key_here'\n"
            "in your terminal before running this script."
        )

def extract_main_html_and_url(html: str) -> tuple[str, str | None]:
    soup = BeautifulSoup(html, "html.parser")

    main = soup.find("main")
    if main is None:
        main = soup.find(id="main-content")
    if main is None:
        main = soup.find(attrs={"role": "main"})
    if main is None:
        main = soup.body or soup

    url = None
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        url = canonical["href"]

    return str(main), url

def simplify_html_for_prompt(html: str) -> str:
    """
    Reduce noise in the HTML before sending it to the model:
    - Keep text content and basic structure.
    - Keep <a href="..."> links.
    - Drop heavy attributes like class, id, data-*, style, etc.
    This lowers token count but preserves meaning and URLs.
    """
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(True):
        attrs_to_keep = {}
        if tag.name == "a" and "href" in tag.attrs:
            attrs_to_keep["href"] = tag["href"]
        tag.attrs = attrs_to_keep

    # Compact the string a bit (remove excessive whitespace)
    return " ".join(str(soup).split())


def build_user_prompt(main_html: str, url: str | None) -> str:
    url_text = url or "unknown"
    simplified = simplify_html_for_prompt(main_html)
    return (
        "Below is the cleaned MAIN CONTENT HTML from a webpage, with non-essential "
        "attributes removed to reduce noise.\n"
        "Use the system instructions to build a new "
        "<main class=\"a11y-page\" role=\"main\"> with an accessible layout "
        "and condensed content.\n\n"
        # f"Canonical URL (if known): {url_text}\n\n"
        "[START SOURCE HTML]\n"
        f"{simplified}\n"
        "[END SOURCE HTML]\n"
    )


def call_model(system_prompt: str, user_prompt: str) -> str:
    client = OpenAI()
    resp = client.responses.create(
        model=MODEL_NAME,
        instructions=system_prompt,
        input=user_prompt,
        max_output_tokens=5000,  # cap for speed
    )
    return resp.output_text


def ensure_single_main_outer_html(model_output: str) -> str:
    """Ensure we get a single <main>…</main> block."""
    soup = BeautifulSoup(model_output, "html.parser")
    main = soup.find("main")
    if main is None:
        wrapped = '<main class="a11y-page" role="main">' + model_output + "</main>"
        soup = BeautifulSoup(wrapped, "html.parser")
        main = soup.find("main")
    return str(main)


def replace_main_and_inject_css(original_html: str, new_main_outer_html: str) -> str:
    soup = BeautifulSoup(original_html, "html.parser")

    main = soup.find("main")
    if main is None:
        main = soup.find(id="main-content")
    if main is None:
        main = soup.find(attrs={"role": "main"})
    if main is None:
        raise RuntimeError("Could not find a <main> element or main-content region in source HTML.")

    new_main_soup = BeautifulSoup(new_main_outer_html, "html.parser")
    model_main = new_main_soup.find("main")
    if model_main is None:
        raise RuntimeError("New main HTML has no <main> element.")

    main.replace_with(model_main)

    # inject CSS (scoped) into <head>
    if soup.head is None:
        head_tag = soup.new_tag("head")
        soup.html.insert(0, head_tag)
    else:
        head_tag = soup.head

    old = head_tag.find("style", id="site-simplify-a11y")
    if old:
        old.decompose()

    style_tag = soup.new_tag("style", id="site-simplify-a11y")
    style_tag.string = ACCESSIBLE_CSS
    head_tag.append(style_tag)

    # Do not add <!DOCTYPE html>; just return what the original had.
    return str(soup)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"          # or "https://www.sunlife.ca"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.route("/")
def home():
    return {"yo": "gurt"}

@app.route("/clean_html", methods=["POST", "OPTIONS"])
@cross_origin(origins="*")
def clean_html():
    # Handle OPTIONS preflight request
    if request.method == "OPTIONS":
        resp = Response()
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return resp

    # Read the HTML file
    html_content = request.data.decode('utf-8')
    
    # Parse the JSON request body to get the HTML
    import json
    try:
        data = json.loads(html_content)
        html_to_clean = data.get('html', '')
    except:
        html_to_clean = html_content
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_to_clean, 'html.parser')
    
    # Helper function to check if an element contains navigation
    def contains_navigation(element):
        """Check if element contains navigation menus or important header content"""
        try:
            if not element:
                return False
            # Check for nav tags
            if element.find('nav'):
                return True
            # Check for navigation-related classes
            for elem in element.find_all(class_=True):
                classes = elem.get('class', [])
                class_str = ' '.join(classes) if isinstance(classes, list) else str(classes)
                if re.search(r'navigation|menu|logo', class_str, re.I):
                    return True
            # Check for logo images
            for img in element.find_all('img'):
                alt_text = img.get('alt', '')
                if alt_text and re.search(r'logo|home', alt_text, re.I):
                    return True
            return False
        except Exception:
            # If there's any error, assume it's navigation and keep it
            return True
    
    # Remove unwanted elements
    unwanted_tags = [
        'style',           # Remove all style tags
        'footer',          # Remove footers
        'iframe',          # Remove iframes
        'noscript',        # Remove noscript tags
    ]
    
    for tag in unwanted_tags:
        for element in soup.find_all(tag):
            element.decompose()
    
    # Remove headers only if they don't contain navigation
    for header in soup.find_all('header'):
        if not contains_navigation(header):
            header.decompose()
    
    # Remove tracking and analytics scripts
    for script in soup.find_all('script'):
        src = script.get('src', '')
        script_id = script.get('id', '')
        # Remove analytics/tracking scripts
        if any(tracker in src.lower() for tracker in [
            'analytics', 'gtag', 'google-analytics', 'googletagmanager',
            'facebook.net', 'fbevents', 'connect.facebook',
            'linkedin.com', 'li.lms-analytics',
            'reddit', 'pixel',
            'pinterest', 'pintrk',
            'tiq.sunlife', 'utag', 'tealium',
            'cookielaw', 'onetrust',
            'decibelinsight',
            'go-mpulse', 'boomerang',
            'chrome-extension://',
            'coveo'
        ]) or 'utag' in script_id or 'BOOMR' in script.get_text():
            script.decompose()
        # Remove JSON-LD structured data
        elif script.get('type') == 'application/ld+json':
            script.decompose()
        # Remove inline tracking code
        elif any(keyword in script.get_text() for keyword in ['utag_data', 'fbq(', 'gtag(', '_linkedin_data_partner_ids']):
            script.decompose()
    
    # Remove browser extension elements
    for element in soup.find_all(['grammarly-desktop-integration', 'simplify-jobs-page-script']):
        element.decompose()
    
    # Remove elements with extension-related classes/ids
    for element in soup.find_all(attrs={'class': re.compile('apolloio|extension-opener|simplify-jobs')}):
        element.decompose()
    
    # Remove preload/prefetch links (performance hints)
    for link in soup.find_all('link', rel=['preload', 'prefetch']):
        link.decompose()
    
    # Remove meta tags except charset and viewport
    for meta in soup.find_all('meta'):
        if not (meta.get('charset') or meta.get('name') in ['viewport', 'charset']):
            meta.decompose()
    
    # Remove canonical and alternate language links (SEO metadata)
    for link in soup.find_all('link', rel=['canonical', 'alternate']):
        link.decompose()
    
    # Remove elements by class/id (cookie banners, hidden elements)
    # Remove by ID
    for element_id in ['onetrust-consent-sdk', 'onetrust-banner-sdk', 'onetrust-pc-sdk']:
        element = soup.find(id=element_id)
        if element:
            element.decompose()
    
    # Remove by class
    for class_name in ['cookie', 'banner']:
        for element in soup.find_all(class_=class_name):
            element.decompose()
    
    # Remove elements with aria-hidden="true"
    for element in soup.find_all(attrs={'aria-hidden': 'true'}):
        element.decompose()
    
    # Remove elements with display:none (case-insensitive, handles various CSS formats)
    for element in soup.find_all(style=True):
        if element and element.attrs:  # Check if element still exists
            style_value = element.get('style', '').lower()
            if re.search(r'display\s*:\s*none', style_value):
                element.decompose()
    
    # Remove all inline styles and style attributes (except on body, html, head for layout)
    for tag in soup.find_all(True):
        # Preserve styles on body, html, head tags for critical layout
        if tag.name not in ['body', 'html', 'head'] and tag.has_attr('style'):
            del tag['style']
        # Clean up other unnecessary attributes (keeping class for structure)
        attrs_to_remove = ['data-sl-aem-component', 'data-sl-component', 'data-cmp-hook-accordion', 
                          'data-bs-target', 'data-bs-toggle', 'data-bs-dismiss', 'data-class', 
                          'data-class-icon', 'data-parsley-validate', 'data-parsley-error-message',
                          'data-parsley-id', 'data-parsley-pattern', 'data-parsley-pattern-message',
                          'data-parsley-required', 'data-parsley-required-message', 'data-single-expansion',
                          'data-title', 'data-fa-i2svg', 'data-icon', 'data-prefix', 'data-cy',
                          'data-grammarly-shadow-root']
        for attr in attrs_to_remove:
            if tag.has_attr(attr):
                del tag[attr]
    
    # Remove empty divs and spans
    for tag in soup.find_all(['div', 'span']):
        if not tag.get_text(strip=True) and not tag.find_all(['img', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            tag.decompose()
    
    # Get the cleaned HTML
    cleaned_html = soup.prettify()

    require_api_key()

    print("Extracting main content and URL ...")
    main_html, url = extract_main_html_and_url(cleaned_html)

    print("Calling OpenAI to generate new accessible <main> ...")
    user_prompt = build_user_prompt(main_html, url)
    raw_model_output = call_model(SYSTEM_PROMPT, user_prompt)

    print("Normalizing model output to a single <main> block ...")
    new_main_outer = ensure_single_main_outer_html(raw_model_output)

    print("Replacing original main-content and injecting a11y CSS ...")
    final_html = replace_main_and_inject_css(cleaned_html, new_main_outer)
    
    resp = Response(final_html, mimetype='text/html; charset=utf-8')
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"

    return resp

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
