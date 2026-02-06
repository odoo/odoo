/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.RamWebsite = publicWidget.Widget.extend({
    selector: ".ram-website",

    /**
     * @override
     */
    start() {
        if (!this.el) return this._super.apply(this, arguments);
        this.initRevealAnimations();
        this.initReviewsSlider();
        this.initGalleryLightbox();
        this.refreshReviewsFromServer();
        return this._super.apply(this, arguments);
    },

    initRevealAnimations() {
        const els = [...this.el.querySelectorAll(".ram-reveal")];
        if (!els.length) return;

        // Prepare elements for animation (hide them now that JS is running)
        for (const el of els) {
            if (!el.classList.contains("is-inview")) {
                el.style.opacity = "0";
                el.style.transform = "translateY(20px)";
                // Force reflow
                void el.offsetHeight;
            }
        }

        if (!("IntersectionObserver" in window)) {
            for (const el of els) this._showReveal(el);
            return;
        }

        const io = new IntersectionObserver(
            (entries) => {
                for (const entry of entries) {
                    if (!entry.isIntersecting) continue;
                    this._showReveal(entry.target);
                    io.unobserve(entry.target);
                }
            },
            { root: null, threshold: 0.1, rootMargin: "0px 0px -5% 0px" }
        );

        for (const el of els) io.observe(el);
    },

    _showReveal(el) {
        el.style.opacity = "1";
        el.style.transform = "translateY(0)";
        el.classList.add("is-inview");
    },

    initReviewsSlider() {
        const slider = this.el.querySelector('[data-ram-slider="reviews"]');
        if (!slider) return;

        const track = slider.querySelector(".ram-slider__track");
        if (!track) return;

        const prevBtn = slider.querySelector('[data-ram-slider-prev="reviews"]');
        const nextBtn = slider.querySelector('[data-ram-slider-next="reviews"]');

        const step = () => {
            const firstCard = track.querySelector(".ram-review");
            if (!firstCard) return 320;
            const cardWidth = firstCard.getBoundingClientRect().width;
            return Math.max(260, Math.round(cardWidth + 14));
        };

        prevBtn?.addEventListener("click", () => {
            track.scrollBy({ left: -step(), behavior: "smooth" });
        });
        nextBtn?.addEventListener("click", () => {
            track.scrollBy({ left: step(), behavior: "smooth" });
        });

        let autoplay = window.setInterval(() => {
            track.scrollBy({ left: step(), behavior: "smooth" });
        }, 7000);

        const stopAutoplay = () => {
            if (!autoplay) return;
            window.clearInterval(autoplay);
            autoplay = null;
        };
        track.addEventListener("pointerdown", stopAutoplay, { passive: true });
        track.addEventListener("wheel", stopAutoplay, { passive: true });
        track.addEventListener("touchstart", stopAutoplay, { passive: true });
    },

    initGalleryLightbox() {
        const lb = document.getElementById("ram_lightbox");
        if (!lb) return;

        const img = lb.querySelector(".ram-lightbox__img");
        const cap = lb.querySelector(".ram-lightbox__caption");
        const closeBtn = lb.querySelector(".ram-lightbox__close");
        let lastTrigger = null;

        const close = () => {
            lb.classList.remove("is-open");
            lb.setAttribute("aria-hidden", "true");
            lb.setAttribute("aria-modal", "false");
            
            // Return focus to the trigger element
            if (lastTrigger) {
                lastTrigger.focus();
            }

            if (img) img.removeAttribute("src");
            if (cap) cap.textContent = "";
        };

        const open = (src, caption, trigger) => {
            lastTrigger = trigger;
            if (img) img.src = src;
            if (cap) cap.textContent = caption || "";
            
            lb.classList.add("is-open");
            // Set aria-hidden to false BEFORE moving focus
            lb.setAttribute("aria-hidden", "false");
            lb.setAttribute("aria-modal", "true");
            
            // Move focus to close button
            setTimeout(() => closeBtn?.focus(), 50);
        };

        closeBtn?.addEventListener("click", close);
        lb.addEventListener("click", (ev) => {
            if (ev.target === lb || ev.target.classList.contains("ram-lightbox__inner")) close();
        });
        
        window.addEventListener("keydown", (ev) => {
            if (ev.key === "Escape" && lb.classList.contains("is-open")) close();
        });

        document.addEventListener("click", (ev) => {
            const btn = ev.target.closest?.(".ram-gallery__item");
            if (!btn) return;
            const full = btn.getAttribute("data-full");
            if (!full) return;
            open(full, btn.getAttribute("data-caption"), btn);
        });

        // Global image error handling to prevent broken icons
        document.addEventListener("error", (ev) => {
            if (ev.target.tagName === "IMG" && ev.target.classList.contains("ram-gallery__img")) {
                if (ev.target.classList.contains("is-placeholder")) return;
                ev.target.src = "/web/static/img/placeholder.png";
                ev.target.classList.add("is-placeholder");
            }
        }, true);
    },

    async refreshReviewsFromServer() {
        const track = document.getElementById("ram_reviews_track");
        if (!track) return;

        try {
            const reviews = await rpc("/ram/reviews", { limit: 12 }, { silent: true });
            if (!Array.isArray(reviews) || !reviews.length) return;

            track.innerHTML = "";
            for (const r of reviews) {
                const card = document.createElement("article");
                card.className = "ram-review";

                const header = document.createElement("header");
                header.className = "ram-review__head";
                
                const author = document.createElement("div");
                author.className = "ram-review__author";
                
                const nameText = document.createElement("div");
                nameText.className = "ram-review__name";
                nameText.textContent = r.author_name || "Customer";
                
                const meta = document.createElement("div");
                meta.className = "ram-review__meta";
                
                const stars = document.createElement("span");
                stars.className = "ram-stars";
                this.renderStars(stars, r.rating);
                
                const source = document.createElement("span");
                source.className = "ram-review__source";
                source.textContent = r.source === "google" ? "Google" : "Customer";
                
                meta.appendChild(stars);
                meta.appendChild(source);
                author.appendChild(nameText);
                author.appendChild(meta);
                header.appendChild(author);

                if (r.review_url) {
                    const link = document.createElement("a");
                    link.className = "ram-review__link";
                    link.href = r.review_url;
                    link.target = "_blank";
                    link.rel = "noopener";
                    link.textContent = "View";
                    header.appendChild(link);
                }

                const text = document.createElement("p");
                text.className = "ram-review__text";
                text.textContent = r.content || "";

                card.appendChild(header);
                card.appendChild(text);
                track.appendChild(card);
            }
        } catch {
            // Ignore failures
        }
    },

    renderStars(target, rating) {
        target.innerHTML = "";
        const safeRating = Math.max(0, Math.min(5, Number(rating) || 0));
        for (let i = 1; i <= 5; i++) {
            const star = document.createElement("i");
            star.className = safeRating >= i ? "fa fa-star" : "fa fa-star-o";
            target.appendChild(star);
        }
    },
});
