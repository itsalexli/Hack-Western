let simplified = false;
let originalHTML = null;

async function fetchNewHTML(html) {
    const url = "http://127.0.0.1:8000/clean_html";
    
    try {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json; charset=UTF-8" },
            body: JSON.stringify({ html })
        });

        console.log('fetch status:', res.status, 'content-type:', res.headers.get('content-type'));

        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }

        const cleanedHtml = await res.text();
        console.log('Cleaned HTML received, length:', cleanedHtml.length);
        
        return cleanedHtml;
    } catch (error) {
        console.error('Error fetching cleaned HTML:', error);
        alert('Error simplifying page. Check console for details.');
        return null;
    }
}

function createButton() {
    // Remove existing button if it exists
    const existingBtn = document.getElementById("simplify-btn");
    if (existingBtn) {
        existingBtn.remove();
    }
    
    const btn = document.createElement("button");
    btn.innerText = simplified ? "Undo" : "Simplify";
    btn.id = "simplify-btn";
    btn.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 999999;
        padding: 12px 24px;
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        font-size: 14px;
        font-weight: bold;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    `;
    btn.addEventListener("click", toggleSimplify);
    document.body.appendChild(btn);
}

function toggleSimplify() {
    if (simplified) {
        location.reload(); // revert to original
    } else {
        // Save original HTML before simplifying
        if (!originalHTML) {
            originalHTML = document.documentElement.outerHTML;
        }
        
        const btn = document.getElementById("simplify-btn");
        if (btn) {
            btn.innerText = "Loading...";
            btn.disabled = true;
        }
        
        fetchNewHTML(originalHTML)
            .then(html => {
                if (!html) {
                    console.error('No HTML returned from server');
                    if (btn) {
                        btn.innerText = "Simplify";
                        btn.disabled = false;
                    }
                    return;
                }
                
                // Inject the button controller script into the cleaned HTML
                const scriptTag = `
                    <script>
                        (function() {
                            let simplified = true;
                            
                            function createButton() {
                                const existingBtn = document.getElementById("simplify-btn");
                                if (existingBtn) {
                                    existingBtn.remove();
                                }
                                
                                const btn = document.createElement("button");
                                btn.innerText = "Undo";
                                btn.id = "simplify-btn";
                                btn.style.cssText = \`
                                    position: fixed;
                                    bottom: 20px;
                                    right: 20px;
                                    z-index: 999999;
                                    padding: 12px 24px;
                                    background-color: #f44336;
                                    color: white;
                                    border: none;
                                    border-radius: 5px;
                                    cursor: pointer;
                                    font-size: 14px;
                                    font-weight: bold;
                                    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
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
                
                // Insert the script before closing body tag
                const htmlWithScript = html.replace('</body>', scriptTag + '</body>');
                
                // Replace the entire document
                document.open();
                document.write(htmlWithScript);
                document.close();
                
                simplified = true;
            })
            .catch(error => {
                console.error('Error in toggleSimplify:', error);
                alert('Error simplifying page. Check console for details.');
                if (btn) {
                    btn.innerText = "Simplify";
                    btn.disabled = false;
                }
            });
    }
}

// Initial button creation
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createButton);
} else {
    createButton();
}