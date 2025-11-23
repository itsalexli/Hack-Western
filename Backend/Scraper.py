from bs4 import BeautifulSoup
import re
from flask import Flask, request, Response
from flask_cors import CORS, cross_origin
import traceback
import os
from openai import OpenAI


app = Flask(__name__)

# You can restrict origins later; for now allow everything while developing
CORS(app, resources={r"/clean_html": {"origins": "*"}})

MODEL_NAME = "gpt-4.1-mini"

SYSTEM_PROMPT = """
You are an accessibility-focused HTML transformer.

Your job:
Take the MAIN CONTENT of an existing webpage and rebuild it into a VERY clear,
condensed layout for older users or people with visual or cognitive overload.

Flow context:
- Another part of the system has already:
  - grabbed the page’s HTML,
  - cleaned it,
  - kept the original header and footer.
- You ONLY see the main-content HTML and a URL.
- Your output will replace the existing main-content region inside the original page.
- The site’s own header and footer stay exactly the same.

Important:
- You ONLY generate the <main> element.
- The surrounding <head> and <body> (including fonts, colours, and brand styling)
  come from the original site via its own CSS files.
- Use a simple, modern, card-based layout with clear sections and large tappable actions.
- A single-column layout is fine. On large screens, you MAY use 2 columns,
  but do not force a rigid grid if it doesn’t fit the content.

Tone and point-of-view:
- Match the tone and voice of the original page as much as possible.
- Talk to the reader directly using “you” and “we”.
- Avoid meta phrases such as “this website is” or “this page explains”.
  Speak as if you are the site talking to the visitor.

STRICT OUTPUT REQUIREMENT:
- Return EXACTLY ONE root element:
    <main class="a11y-page" role="main"> … </main>
- No text, comments, or whitespace BEFORE or AFTER this <main> element.
- This <main> block will be used directly as element.outerHTML in the browser.

You MUST:
- Output ONE <main class="a11y-page" role="main">…</main>.
- Use short, clear sentences, but include enough detail to be genuinely helpful.
- Strongly reduce clutter and marketing fluff.
- Make text easy to read:
  - short paragraphs,
  - clear headings,
  - bullet-like lists for complex points.
- Use <a> elements with real href URLs for interactive buttons and chips,
  reusing URLs from the source HTML whenever possible.
- Keep layout changes confined INSIDE your <main>. Do NOT assume anything
  about header height or global page structure.

You SHOULD (but may adapt as needed for the page):
- Start with an overview section explaining what the page offers and who it helps.
- Provide a clear “primary actions” area (key tasks as large, tappable items).
- Provide condensed content and quick facts in separate sections or cards.
- Organize major chunks of content into CARDS (a11y-card).

You MAY:
- Rename section headings to better match the content.
- Drop sections that do not make sense for this page.
- Add extra short sections (e.g., “Eligibility”, “Costs”, “Examples”, “How it works”)
  if they help understanding.
- Use a single-column layout if that is clearer for this page.

You MUST NOT:
- Output <html>, <head>, <body>, <style>, or <script>.
- Output markdown or code fences.
- Copy long paragraphs from the original.
- Invent actions or links that are not conceptually present in the source.
- Add large fixed top margins or positioning that tries to “move below the header”.
  The page header is handled elsewhere; just structure the content.

------------------------------
READING LEVEL & CONTENT
------------------------------

Audience:
- Older adults
- People with low vision.
- People who get overwhelmed by busy layouts.

Language:
- Aim for grade 5–7 reading level.
- Sentences 8–16 words long.
- Use common, everyday words.
- Explain any technical term in one simple sentence.

Keep only:
- What the page is about.
- Who it is for.
- Main actions (buttons/flows).
- Key facts, limits, or warnings.
- Simple “next steps”.

Include:
- Clear explanations of what the product/service does.
- Plain-language explanations of benefits and important conditions.
- Enough detail that the reader could make a basic decision or know what to ask.

Remove:
- Marketing hype and filler.
- Long intros and stories.
- Repetition.
- Most fine-print legal text (unless absolutely critical to understanding).

Ideal length: about 700–1400 words.
Prefer lists and short paragraphs over large text blocks.

------------------------------
STRUCTURE (GUIDELINE, CARD-BASED)
------------------------------

Always organize the main content into CARDS.

- Every major section (overview, primary actions, condensed content,
  quick facts, eligibility, etc.) should be wrapped in an element with
  class="a11y-card".
- On large screens you MAY place cards in two columns.
- On smaller screens, cards should stack in a single column
  (the CSS handles this with media queries).

Use this as a guideline. You can adjust the number of sections and columns
as needed to best fit the content, but always keep
<main class="a11y-page" role="main"> as the root element.

Example structure:

<main class="a11y-page" role="main">
  <section class="a11y-hero-row">
    <article class="a11y-card a11y-overview-card">…</article>
    <aside class="a11y-card a11y-actions-card" aria-label="Primary actions">…</aside>
  </section>

  <section class="a11y-content-section">
    <article class="a11y-card a11y-condensed-content">…</article>
  </section>

  <section class="a11y-content-grid">
    <article class="a11y-card">…</article>
    <aside class="a11y-card a11y-quick-facts">…</aside>
  </section>

  <footer class="a11y-footer">…</footer>
</main>

Use these class names where they make sense:
- a11y-page, a11y-hero-row, a11y-card, a11y-overview-card, a11y-actions-card,
  a11y-content-section, a11y-content-grid, a11y-condensed-content,
  a11y-quick-facts, a11y-section-label, a11y-site-header, a11y-site-id,
  a11y-favicon, a11y-site-text, a11y-site-title, a11y-site-url,
  a11y-pill-badge, a11y-pill-dot, a11y-hero-summary, a11y-hero-cta-row,
  a11y-primary-btn, a11y-secondary-btn, a11y-actions-layout,
  a11y-primary-actions, a11y-action-chip, a11y-meta-row, a11y-list,
  a11y-tag-row, a11y-tag, a11y-footer, a11y-large-text, a11y-important-text.

You do NOT have to use every class, but when you need that role, prefer that name.
The labels “Get a quote”, “Find an advisor”, etc. are EXAMPLES only; always
derive labels from the input page.

------------------------------
ACTIONS & LINKS
------------------------------

For CTAs and chips:

- Use <a> elements, not <button>.
- Reuse href URLs from important links in the source HTML.
- If multiple links go to the same main action, pick one.
- If you cannot confidently choose a specific URL, link to the main page URL
  given in the prompt.

------------------------------
FOOTER / SOURCE
------------------------------

End with a footer like:

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

Use the canonical URL or the provided URL when possible.

------------------------------
GENERAL REMINDERS
------------------------------

- Output exactly one <main class="a11y-page" role="main">…</main> element.
- No extra text before or after this main element.
- Make text large and easy to read by applying class="a11y-large-text"
  to most user-facing paragraphs and list items.
- Use <a> tags with href URLs for interactive buttons and chips,
  reusing real URLs from the source HTML when available.
- Talk directly to the reader (“you”, “we”), and avoid meta “this website” phrasing.
-------------------------------
Design
-------------------------------
- MAKE SURE TO Access the html in a browser and see how it looks visually, then try to
    match the design as close as possible with the exact colours and fonts.
""" 

ACCESSIBLE_CSS = r"""

.a11y-page {
  margin: 0 auto 40px;
  max-width: 1200px;
  padding: 0 24px 40px;
  font-size: 1.2rem;
  line-height: 1.8;
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
}

@media (max-width: 900px) {
  .a11y-hero-row,
  .a11y-content-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

.a11y-card {
  background: rgba(255, 255, 255, 0.98);
  border-radius: 22px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  padding: 24px 24px 20px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
}

/* Make anchors with button classes look like actual buttons */
a.a11y-primary-btn,
a.a11y-secondary-btn {
  text-decoration: none;
  color: inherit;
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
}

/* Top labels / header */

.a11y-section-label {
  font-size: 0.78rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  opacity: 0.7;
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
  gap: 10px;
}

.a11y-primary-btn,
.a11y-secondary-btn {
  border-radius: 999px;
  padding: 10px 18px;
  font-size: 1rem;
  cursor: pointer;
  border: 1px solid rgba(0, 0, 0, 0.14);
  background: #fff;
  box-shadow: 0 0 0 rgba(0, 0, 0, 0.0);
  transition: box-shadow 150ms ease-out, transform 150ms ease-out,
              background-color 150ms ease-out, border-color 150ms ease-out;
}

.a11y-primary-btn {
  font-weight: 600;
}

.a11y-secondary-btn {
  opacity: 0.95;
}

.a11y-primary-btn:hover,
.a11y-secondary-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 9px 22px rgba(0, 0, 0, 0.14);
}

/* Actions panel */

.a11y-actions-layout {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.a11y-primary-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

/* Chips */

.a11y-action-chip {
  text-decoration: none;
  color: inherit;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  flex: 1 1 45%;
  min-width: 180px;
  border-radius: 18px;
  padding: 12px 14px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: rgba(255, 255, 255, 0.98);
  cursor: pointer;
  text-align: left;
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.06);
  transition: box-shadow 150ms ease-out, transform 150ms ease-out,
              border-color 150ms ease-out, background-color 150ms ease-out;
}

.a11y-action-chip span:first-child {
  font-weight: 600;
  margin-bottom: 4px;
}

.a11y-action-chip span:last-child {
  font-size: 0.95rem;
  opacity: 0.9;
}

.a11y-action-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 9px 20px rgba(0, 0, 0, 0.12);
}

/* Meta row */

.a11y-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 0.8rem;
  opacity: 0.8;
}

.a11y-meta-row span {
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.03);
}

/* Lists */

.a11y-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-left: 0;
}

.a11y-list li {
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(0, 0, 0, 0.03);
}

.a11y-list li strong {
  display: block;
  margin-bottom: 4px;
  font-weight: 600;
}

/* Tags */

.a11y-tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.a11y-tag {
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 0.85rem;
  background: rgba(0, 0, 0, 0.04);
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
  border-top: 1px dashed rgba(0, 0, 0, 0.1);
  font-size: 0.95rem;
  opacity: 0.9;
}

.a11y-footer a {
  text-decoration: underline;
}

/* Text sizing helpers */

.a11y-large-text {
  font-size: 1.15em;
}

.a11y-important-text {
  font-weight: 600;
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
        max_output_tokens=2000,  # cap for speed
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

    # Create response with explicit headers
    # resp = Response(cleaned_html, mimetype='text/html; charset=utf-8')
    # resp.headers["Access-Control-Allow-Origin"] = "*"
    # resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    # resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"

    require_api_key()

    print("Extracting main content and URL ...")
    main_html, url = extract_main_html_and_url(cleaned_html)

    print("Calling OpenAI to generate new accessible <main> ...")
    user_prompt = build_user_prompt(cleaned_html, url)
    raw_model_output = call_model(SYSTEM_PROMPT, user_prompt)

    print("Normalizing model output to a single <main> block ...")
    new_main_outer = ensure_single_main_outer_html(raw_model_output)

    print("Replacing original main-content and injecting a11y CSS ...")
    final_html = replace_main_and_inject_css(html_to_clean, new_main_outer)
    
    resp = Response(final_html, mimetype='text/html; charset=utf-8')
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"

    return resp

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)


# def main():
#     """Main function to run the cleaner"""
#     import os
    
#     # Get the directory where this script is located
#     script_dir = os.path.dirname(os.path.abspath(__file__))
    
#     input_file = os.path.join(script_dir, 'Sample2.txt')
#     output_file = os.path.join(script_dir, 'cleaned_output.html')
    
#     print(f"Cleaning HTML from {input_file}...")
    
#     try:
#         # Read original file to get its size
#         with open(input_file, 'r', encoding='utf-8') as file:
#             original_html = file.read()
#         original_size = len(original_html)
        
#         cleaned_html = clean_html(input_file)
#         cleaned_size = len(cleaned_html)
        
#         # Calculate reduction
#         reduction = original_size - cleaned_size
#         reduction_percent = (reduction / original_size * 100) if original_size > 0 else 0
        
#         # Save to output file
#         with open(output_file, 'w', encoding='utf-8') as file:
#             file.write(cleaned_html)
        
#         print(f"✓ Cleaned HTML saved to {output_file}")
#         print(f"✓ Original size: {original_size:,} characters")
#         print(f"✓ Cleaned size:  {cleaned_size:,} characters")
#         print(f"✓ Reduced by:    {reduction:,} characters ({reduction_percent:.1f}%)")
        
#     except FileNotFoundError:
#         print(f"Error: Could not find {input_file}")
#     except Exception as e:
#         print(f"Error: {e}")


# if __name__ == "__main__":
#     main()