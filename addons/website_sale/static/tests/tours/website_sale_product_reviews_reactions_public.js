import { registry } from "@web/core/registry";

registry
    .category('web_tour.tours')
    .add('website_sale_product_reviews_reactions_public', {
        url: '/shop?search=Storage Box Test',
        steps: () => [
            {
                trigger: '.oe_product_cart a:contains("Storage Box Test")',
                run: "click",
                expectUnloadPage: true,
            },
            {
                content: "The collapsed reviews must not have booted the chatter",
                trigger: '#o_product_page_reviews_content:hidden:not(:has(#chatterRoot))',
                run: () => {
                    const requested = performance
                        .getEntriesByType('resource')
                        .some(entry => entry.name.includes('/web/bundle/portal.assets_chatter'));
                    if (requested) {
                        throw new Error(
                            "portal.assets_chatter was loaded although the reviews are collapsed"
                        );
                    }
                },
            },
            {
                trigger: '.o_product_page_reviews_title',
                run: "click",
            },
            {
                trigger: "#chatterRoot:shadow .o-mail-Message-textContent:contains(Bad box!)",
                run: "hover && click",
            },
            {
                trigger: "#chatterRoot:shadow .o-mail-Message-actions",
                run: async () => {
                    const addReactionButton = document.querySelector('#chatterRoot').shadowRoot.querySelector("[title='Add a Reaction']")
                    if (addReactionButton) {
                        throw new Error("Non-authenticated user should not be able to add a reaction to a message");
                    }
                },
            },
            {
                trigger: "#chatterRoot:shadow .o-mail-Message-core",
                run: () => {
                    const reactionButton = document.querySelector("#chatterRoot").shadowRoot.querySelector(".o-mail-MessageReaction")
                    reactionButton.dispatchEvent(new Event("mouseenter"));
                },
            },
            {
                trigger: "#chatterRoot:shadow .o-mail-MessageReactionList-preview",
                run: "click",
            },
            {
                trigger: "#chatterRoot:shadow .o-mail-MessageReactionMenu",
            },
            {
                trigger: "#chatterRoot:shadow .o-mail-Message-core",
                run: () => {
                    const addReaction = document.querySelector("#chatterRoot").shadowRoot.querySelector(".o-mail-MessageReactions-add")
                    if (addReaction) {
                        throw new Error("Non-authenticated user should not be able to add a reaction to a message");
                    }
                },
            },
        ],
   });
