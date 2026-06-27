from playwright.sync_api import sync_playwright
import re


def extract_episode_number(text):
    match = re.search(r"(\d+)\s*(?:v\d+)?\s*$", text, re.IGNORECASE)
    if match:
        return int(match.group(1))

    fallback = re.findall(r"\d+", text)
    return int(fallback[-1]) if fallback else None


def get_magnet_url(s_url, e, a):
    url = s_url + "shows/" + a.lower().replace(" ", "-") + "/"
    print("Target URL:", url)

    with sync_playwright() as p:

        context = p.chromium.launch_persistent_context(
            user_data_dir="pw_cache",
            headless=True,
            viewport={"width": 1280, "height": 800},
        )

        # 🚀 block heavy assets
        def block(route):
            if route.request.resource_type in ("image", "font", "media"):
                route.abort()
            else:
                route.continue_()

        context.route("**/*", block)

        page = context.new_page()

        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector("label.episode-title")

        raw = page.evaluate("""
        () => {
            const episodes = [];

            document.querySelectorAll("label.episode-title").forEach(label => {
                const text = label.textContent;
                const container = label.nextElementSibling;
                if (!container) return;

                const entry = {
                    title: text,
                    qualities: {}
                };

                let currentQuality = null;

                container.childNodes.forEach(node => {

                    // detect quality label
                    if (node.tagName === "LABEL" && node.classList.contains("links")) {
                        currentQuality = node.textContent.trim();
                    }

                    // detect magnet link
                    if (node.tagName === "A" && node.href && node.href.startsWith("magnet:?")) {
                        if (currentQuality) {
                            entry.qualities[currentQuality] = node.href;
                        }
                    }
                });

                episodes.push(entry);
            });

            return episodes;
        }
        """)

        context.close()

    # 🚀 build final structured dict
    episodes_dict = {}

    for ep in raw:
        ep_num = extract_episode_number(ep["title"])
        if ep_num is None:
            continue

        episodes_dict[ep_num] = ep["qualities"]

    # 🚀 sort by episode number
    episodes_dict = dict(sorted(episodes_dict.items(), key=lambda x: x[0]))

    return episodes_dict


if __name__ == "__main__":
    base_url = "https://subsplease.org/"
    anime = "blue lock"

    result = get_magnet_url(base_url, 1, anime)

    for ep, qualities in result.items():
        print(f"\nEpisode {ep}")
        for q, magnet in qualities.items():
            print(f"  {q}: {magnet}")