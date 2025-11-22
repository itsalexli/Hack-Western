from bs4 import BeautifulSoup
import re
import traceback

def clean_html(file_path):
    """
    Clean HTML file by removing unnecessary elements while preserving content structure.
    
    Args:
        file_path: Path to the HTML file to clean
    
    Returns:
        Cleaned HTML as a string
    """
    
    # Read the HTML file
    with open(file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
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
    
    return cleaned_html


def main():
    """Main function to run the cleaner"""
    import os
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    input_file = os.path.join(script_dir, 'Sample2.txt')
    output_file = os.path.join(script_dir, 'cleaned_output.html')
    
    print(f"Cleaning HTML from {input_file}...")
    
    try:
        # Read original file to get its size
        with open(input_file, 'r', encoding='utf-8') as file:
            original_html = file.read()
        original_size = len(original_html)
        
        cleaned_html = clean_html(input_file)
        cleaned_size = len(cleaned_html)
        
        # Calculate reduction
        reduction = original_size - cleaned_size
        reduction_percent = (reduction / original_size * 100) if original_size > 0 else 0
        
        # Save to output file
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(cleaned_html)
        
        print(f"✓ Cleaned HTML saved to {output_file}")
        print(f"✓ Original size: {original_size:,} characters")
        print(f"✓ Cleaned size:  {cleaned_size:,} characters")
        print(f"✓ Reduced by:    {reduction:,} characters ({reduction_percent:.1f}%)")
        
    except FileNotFoundError:
        print(f"Error: Could not find {input_file}")
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()