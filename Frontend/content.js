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
        btn.innerText = "Simplify";
        btn.disabled = true;
        btn.style.backgroundColor = "#999";
        btn.style.cursor = "not-allowed";
    }
    
    btn.addEventListener("click", toggleSimplify);
    document.body.appendChild(btn);
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
                            z-index: 999999;
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