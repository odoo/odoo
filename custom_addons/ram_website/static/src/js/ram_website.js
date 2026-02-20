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
        const nextBtn = lb.querySelector(".js_ram_lightbox_next");
        const prevBtn = lb.querySelector(".js_ram_lightbox_prev");
        const zoomBtn = lb.querySelector(".js_ram_lightbox_zoom");

        let lastTrigger = null;
        let galleryItems = [];
        let currentIndex = -1;
        let isZoomed = false;

        const syncGalleryItems = () => {
            galleryItems = [...document.querySelectorAll(".ram-gallery__item")];
        };

        const close = () => {
            lb.classList.remove("is-open");
            lb.classList.remove("is-zoomed");
            isZoomed = false;
            lb.setAttribute("aria-hidden", "true");
            lb.setAttribute("aria-modal", "false");
            
            if (lastTrigger) {
                lastTrigger.focus();
            }

            if (img) {
                img.removeAttribute("src");
                img.style.transform = "";
            }
            if (cap) cap.textContent = "";
        };

        const open = (index, trigger) => {
            if (index < 0 || index >= galleryItems.length) return;
            
            currentIndex = index;
            const btn = galleryItems[index];
            const src = btn.getAttribute("data-full");
            const caption = btn.getAttribute("data-caption");
            
            lastTrigger = trigger || btn;
            if (img) {
                img.src = src;
                img.style.transform = "";
            }
            if (cap) cap.textContent = caption || "";
            
            lb.classList.add("is-open");
            lb.classList.remove("is-zoomed");
            isZoomed = false;
            lb.setAttribute("aria-hidden", "false");
            lb.setAttribute("aria-modal", "true");
            
            setTimeout(() => closeBtn?.focus(), 50);
        };

        const navigate = (dir) => {
            let nextIdx = currentIndex + dir;
            if (nextIdx < 0) nextIdx = galleryItems.length - 1;
            if (nextIdx >= galleryItems.length) nextIdx = 0;
            open(nextIdx);
        };

        const toggleZoom = () => {
            isZoomed = !isZoomed;
            lb.classList.toggle("is-zoomed", isZoomed);
        };

        closeBtn?.addEventListener("click", close);
        nextBtn?.addEventListener("click", () => navigate(1));
        prevBtn?.addEventListener("click", () => navigate(-1));
        zoomBtn?.addEventListener("click", toggleZoom);

        lb.addEventListener("click", (ev) => {
            if (ev.target === lb || ev.target.classList.contains("ram-lightbox__inner")) close();
        });
        
        window.addEventListener("keydown", (ev) => {
            if (!lb.classList.contains("is-open")) return;
            if (ev.key === "Escape") close();
            if (ev.key === "ArrowRight") navigate(1);
            if (ev.key === "ArrowLeft") navigate(-1);
        });

        document.addEventListener("click", (ev) => {
            const btn = ev.target.closest?.(".ram-gallery__item");
            if (!btn) return;
            syncGalleryItems();
            const idx = galleryItems.indexOf(btn);
            if (idx !== -1) open(idx, btn);
        });

        // Add Category Filtering logic here
        document.addEventListener("click", (ev) => {
            const filterBtn = ev.target.closest(".js_ram_filter_category");
            if (!filterBtn) return;
            
            const categoryId = filterBtn.dataset.categoryId;
            
            // Update active button state
            document.querySelectorAll(".js_ram_filter_category").forEach(b => {
                b.classList.toggle("active", b === filterBtn);
            });
            
            // Filter items
            document.querySelectorAll(".js_ram_dish_item").forEach(item => {
                if (categoryId === "all") {
                    item.classList.remove("d-none");
                } else {
                    item.classList.toggle("d-none", !item.classList.contains(`cat-${categoryId}`));
                }
            });
        });

        // Global image error handling to prevent broken icons
        document.addEventListener("error", (ev) => {
            if (ev.target.tagName === "IMG" && ev.target.classList.contains("ram-gallery__img")) {
                if (ev.target.classList.contains("is-placeholder")) return;
                
                console.warn("🖼️ Image load failed:", ev.target.src);
                
                // If it's a gallery image, try the 'full' image if the thumbnail fails
                const btn = ev.target.closest(".ram-gallery__item") || ev.target.closest(".ram-location__media");
                const full = btn?.getAttribute("data-full");
                
                if (full && ev.target.src !== full) {
                    console.log("🔄 Trying full image fallback:", full);
                    ev.target.src = full;
                } else if (ev.target.src.includes('image_1024')) {
                    const raw = ev.target.src.replace('image_1024', 'image_1920');
                    console.log("🔄 Trying raw image fallback:", raw);
                    ev.target.src = raw;
                } else {
                    console.error("❌ All image fallbacks failed for:", ev.target.src);
                    ev.target.src = "/web/static/img/placeholder.png";
                    ev.target.classList.add("is-placeholder");
                }
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

                const avatarWrapper = document.createElement("div");
                avatarWrapper.className = "ram-review__avatar-wrapper";
                if (r.author_photo_url) {
                    const avatar = document.createElement("img");
                    avatar.className = "ram-review__avatar";
                    avatar.src = r.author_photo_url;
                    avatarWrapper.appendChild(avatar);
                } else {
                    const placeholder = document.createElement("div");
                    placeholder.className = "ram-review__avatar ram-review__avatar--placeholder";
                    placeholder.textContent = (r.author_name || "C").charAt(0).toUpperCase();
                    avatarWrapper.appendChild(placeholder);
                }
                
                const authorInfo = document.createElement("div");
                authorInfo.className = "ram-review__author-info";

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
                authorInfo.appendChild(nameText);
                authorInfo.appendChild(meta);
                
                author.appendChild(avatarWrapper);
                author.appendChild(authorInfo);
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
