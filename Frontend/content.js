if (!window.__bottomRightCircleAdded) {
    window.__bottomRightCircleAdded = true;

    const container = document.createElement("div");
    container.className = "container";

    // const title = document.createElement("p");
    // title.textContent = "Simply";
    // container.appendChild(title);

    const toggle = document.createElement("label");
    toggle.className = "switch";

    const input = document.createElement("input");
    input.type = "checkbox";
    toggle.appendChild(input);

    const span = document.createElement("span");
    span.className = "slider";
    toggle.appendChild(span);

    let simplify = false;

    input.onclick = async () => {
        simplify = !simplify;
        console.log(simplify);
        const html = document.documentElement.outerHTML;

        const url = "sadkjashfkjdakfgja";
        try {
            const response = await fetch(url, {
                method: "POST", 
                body: JSON.stringify({ html: html }),
                headers: {
                    "Content-type": "application/json; charset=UTF-8"
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            console.log(result);
        } catch (error) {
            console.error("Error fetching data:", error);
        }
    };

    container.appendChild(toggle);

    // prevent clicks on the switch/slider from bubbling up to the container
    input.addEventListener('click', (ev) => ev.stopPropagation());
    toggle.addEventListener('click', (ev) => ev.stopPropagation());

    container.addEventListener("click", (e) => {
        
        if (e.target.tagName === "INPUT" || e.target.closest("input")) return;
        container.classList.toggle("pinned");
    });

    document.body.appendChild(container);
}