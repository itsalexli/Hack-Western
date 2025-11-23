let simplified = false;
let originalHTML = null;
let simplifiedHTML = null;
let isLoading = false;

async function fetchNewHTML(html) {
    const url = "http://127.0.0.1:8000/clean_html";
    
    try {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json; charset=UTF-8" },
            body: JSON.stringify({ html }),
            signal: AbortSignal.timeout(60000)
        });

        console.log('fetch status:', res.status);

        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }

        const cleanedHtml = await res.text();
        console.log('Simplified HTML received, length:', cleanedHtml.length);
        
        return cleanedHtml;
    } catch (error) {
        console.error('Error fetching simplified HTML:', error);
        return null;
    }
}

function createButton() {
    const existingBtn = document.getElementById("simplify");
    if (existingBtn) {
        existingBtn.remove();
    }

    const btn = document.createElement("button");
    btn.id = "simplify";

    // Base overlay styles – always apply these
    btn.style.position = "fixed";
    btn.style.bottom = "20px";
    btn.style.right = "20px";
    btn.style.zIndex = "2147483648"; // higher than the iframe so it's visible
    btn.style.padding = "10px 20px";
    btn.style.color = "white";
    btn.style.border = "none";
    btn.style.borderRadius = "5px";
    btn.style.fontSize = "16px";

    // State-specific styles
    if (isLoading) {
        btn.innerText = "Loading...";
        btn.disabled = true;
        btn.style.backgroundColor = "#999";
        btn.style.cursor = "not-allowed";
    } else if (simplified) {
        btn.innerText = "Undo";
        btn.disabled = false;
        btn.style.backgroundColor = "#ff4444";
        btn.style.cursor = "pointer";
    } else if (simplifiedHTML) {
        btn.innerText = "Simplify";
        btn.disabled = false;
        btn.style.backgroundColor = "#4CAF50";
        btn.style.cursor = "pointer";
    } else {
        // Initial state before simplifiedHTML is ready
        btn.innerText = "Simplify";
        btn.disabled = true;
        btn.style.backgroundColor = "#999";
        btn.style.cursor = "not-allowed";
    }

    btn.addEventListener("click", toggleSimplify);
    document.body.appendChild(btn);
}


function injectElevenLabsPanel() {
  if (document.getElementById("elevenlabs-panel-iframe")) return;

  const iframe = document.createElement("iframe");
  iframe.id = "elevenlabs-panel-iframe";

  const pageUrl = encodeURIComponent(window.location.href);
  iframe.src = chrome.runtime.getURL(`eleven-panel.html?url=${pageUrl}`);

  iframe.allow = "microphone; autoplay";

  iframe.style.position = "fixed";
  iframe.style.bottom = "20px";
  iframe.style.left = "20px";
  iframe.style.width = "360px";
  iframe.style.height = "100px";
  iframe.style.border = "none";
  iframe.style.borderRadius = "16px";
  iframe.style.zIndex = "2147483647";
  iframe.style.boxShadow = "0 12px 30px rgba(0,0,0,0.35)";
  iframe.style.background = "transparent";
  iframe.style.overflow = "hidden";

  document.documentElement.appendChild(iframe);
}


function updateButtonState() {
    const btn = document.getElementById("simplify");
    if (!btn) return;
    
    if (isLoading) {
        btn.innerText = "Loading...";
        btn.disabled = true;
        btn.style.backgroundColor = "#999";
        btn.style.cursor = "not-allowed";
    } else if (simplified) {
        btn.innerText = "Undo";
        btn.disabled = false;
        btn.style.backgroundColor = "#ff4444";
        btn.style.cursor = "pointer";
    } else if (simplifiedHTML) {
        btn.innerText = "Simplify";
        btn.disabled = false;
        btn.style.backgroundColor = "#4CAF50";
        btn.style.cursor = "pointer";
    } else {
        btn.innerText = "Failed";
        btn.disabled = true;
        btn.style.backgroundColor = "#999";
        btn.style.cursor = "not-allowed";
    }
}

function toggleSimplify() {
    if (simplified) {
        location.reload();
    } else if (simplifiedHTML && !isLoading) {  // ← Added !isLoading check
        console.log('Using cached simplified HTML');  // ← Debug log
        
        const scriptTag = `
            <script>
                (function() {
                    let simplified = true;
                    
                    function createButton() {
                        const existingBtn = document.getElementById("simplify");
                        if (existingBtn) {
                            existingBtn.remove();
                        }
                        
                        const btn = document.createElement("button");
                        btn.innerText = "Undo";
                        btn.id = "simplify";
                        btn.style.cssText = \`
                            position: fixed;
                            bottom: 20px;
                            right: 20px;
                            z-index: 2147483648;
                            padding: 10px 20px;
                            background: #ff4444;
                            color: white;
                            border: none;
                            border-radius: 5px;
                            font-size: 16px;
                            cursor: pointer;
                        \`;
                        btn.addEventListener("click", function() {
                            location.reload();
                        });
                        document.body.appendChild(btn);
                    }
                    
                    if (document.readyState === 'loading') {
                        document.addEventListener('DOMContentLoaded', createButton);
                    } else {
                        createButton();
                    }
                })();
            </script>
        `;
        
        const htmlWithScript = simplifiedHTML.replace('</body>', scriptTag + '</body>');
        
        document.open();
        document.write(htmlWithScript);
        document.close();
        
        // Don't set simplified = true here, it doesn't matter since page reloads
    }
}

async function preFetchSimplifiedVersion() {
    // ← FIX: Check if already loaded to prevent re-fetching
    if (simplifiedHTML) {
        console.log('Simplified version already cached, skipping fetch');
        return;
    }
    
    console.log('Pre-fetching simplified version...');
    isLoading = true;
    updateButtonState();
    
    originalHTML = document.documentElement.outerHTML;
    simplifiedHTML = await fetchNewHTML(originalHTML);
    
    isLoading = false;
    
    if (simplifiedHTML) {
        console.log('✓ Simplified version ready!');
    } else {
        console.error('✗ Failed to fetch simplified version');
    }
    
    updateButtonState();
}

function initialize() {
    // ← FIX: Only initialize once
    if (window.__simplifyInitialized) {
        console.log('Already initialized, skipping');
        return;
    }
    window.__simplifyInitialized = true;
    
    createButton();
    injectElevenLabsPanel(); // <<< add this line
    
    // Start pre-fetching after a short delay
    setTimeout(() => {
        preFetchSimplifiedVersion();
    }, 1000);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}