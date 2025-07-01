import {
    SIZES,
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    openFormView,
    patchUiSize,
    scroll,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { onRpc, patchWithCleanup, preloadBundle } from "@web/../tests/web_test_helpers";

import { GifPicker } from "@mail/discuss/gif_picker/common/gif_picker";

describe.current.tags("desktop");
defineMailModels();
preloadBundle("web.assets_emoji");

let gifId = 0;
const gifFactory = (count = 1, options = {}) => {
    const gifs = [];
    for (let i = 0; i < count; i++) {
        gifs.push({
            id: `${gifId}`,
            title: "",
            media_formats: {
                tinygif: {
                    url: options.url || "https://media.tenor.com/np49Y1vrJO8AAAAM/crying-cry.gif",
                    duration: 0,
                    preview: "",
                    dims: [220, 190],
                    size: 1007885,
                },
            },
            created: 1654414453.782169,
            content_description: "Cry GIF",
            itemurl: "https://tenor.com/view/cry-gif-25866484",
            url: "https://tenor.com/bUHdw.gif",
            tags: ["cry"],
            flags: [],
            hasaudio: false,
        });
        gifId++;
    }
    return gifs;
};

const rpc = {
    search: {
        results: gifFactory(2),
        next: "CAgQpIGj_8WN_gIaHgoKAD-_xMQ20dMU_xIQ1MVHUnSAQxC98Y6VAAAAADAI",
    },
    categories: {
        locale: "en",
        tags: [
            {
                searchterm: "cry",
                path: "/v2/search?q=cry&locale=en&component=categories&contentfilter=low",
                image: "https://media.tenor.com/6uIlQAHIkNoAAAAM/cry.gif",
                name: "#cry",
            },
            {
                searchterm: "yes",
                path: "/v2/search?q=yes&locale=en&component=categories&contentfilter=low",
                image: "https://media.tenor.com/UVmpVqlpVhQAAAAM/yess-yes.gif",
                name: "#yes",
            },
            {
                searchterm: "no",
                path: "/v2/search?q=no&locale=en&component=categories&contentfilter=low",
                image: "https://media.tenor.com/aeswYw-86k8AAAAM/no-nooo.gif",
                name: "#no",
            },
            {
                searchterm: "lol",
                path: "/v2/search?q=lol&locale=en&component=categories&contentfilter=low",
                image: "https://media.tenor.com/BiseY2UXovAAAAAM/lmfao-laughing.gif",
                name: "#lol",
            },
        ],
    },
};

test("composer should display a GIF button", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await contains("button[aria-label='GIFs']");
});

test("Composer GIF button should open the GIF picker", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='GIFs']");
    await contains(".o-discuss-GifPicker");
});

test("Searching for a GIF", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    onRpc("/discuss/gif/search", () => rpc.search);
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='GIFs']");
    await insertText("input[placeholder='Search for a GIF']", "search");
    await contains("i[aria-label='back']");
    await contains(".o-discuss-Gif", { count: 2 });
});

test("Open a GIF category trigger the search for the category", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    onRpc("/discuss/gif/categories", () => rpc.categories);
    onRpc("/discuss/gif/search", () => rpc.search);
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='GIFs']");
    await click("img[data-src='https://media.tenor.com/6uIlQAHIkNoAAAAM/cry.gif']");
    await contains(".o-discuss-Gif", { count: 2 });
    await contains("input[placeholder='Search for a GIF']", { value: "cry" });
});

test("Can have GIF categories with same name", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    onRpc("/discuss/gif/categories", () => {
        return {
            locale: "en",
            tags: [
                {
                    searchterm: "duplicate",
                    path: "/v2/search?q=duplicate&locale=en&component=categories&contentfilter=low",
                    image: "https://media.tenor.com/BiseY2UXovAAAAAM/duplicate.gif",
                    name: "#duplicate",
                },
                {
                    searchterm: "duplicate",
                    path: "/v2/search?q=duplicate&locale=en&component=categories&contentfilter=low",
                    image: "https://media.tenor.com/BiseY2UXovAAAAAM/duplicate.gif",
                    name: "#duplicate",
                },
            ],
        };
    });
    onRpc("/discuss/gif/search", () => rpc.search);
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='GIFs']");
    await contains("img[data-src='https://media.tenor.com/BiseY2UXovAAAAAM/duplicate.gif']", {
        count: 2,
    });
});

test("Reopen GIF category list when going back", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    onRpc("/discuss/gif/categories", () => rpc.categories);
    onRpc("/discuss/gif/search", () => rpc.search);
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='GIFs']");
    await click("img[data-src='https://media.tenor.com/6uIlQAHIkNoAAAAM/cry.gif']");
    await click("i[aria-label='back']");
    await contains(".o-discuss-GifPicker div[aria-label='list']");
});

test("Add GIF to favorite", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    onRpc("/discuss/gif/categories", () => rpc.categories);
    onRpc("/discuss/gif/search", () => rpc.search);
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='GIFs']");
    await click("img[data-src='https://media.tenor.com/6uIlQAHIkNoAAAAM/cry.gif']");
    await click(":nth-child(1 of div) > .o-discuss-Gif .fa-star-o");
    await contains(".o-discuss-Gif .fa-star");
    await click("i[aria-label='back']");
    await click(".o-discuss-GifPicker div[aria-label='list-item']", { text: "Favorites" });
    await contains(".o-discuss-Gif");
});

test("Chatter should not have the GIF button", async () => {
    const pyEnv = await startServer();
    await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    await openFormView("res.partner", partnerId);
    await click("button", { text: "Log note" });
    await contains("button[aria-label='GIFs']", { count: 0 });
});

test("Composer GIF button should open the GIF picker keyboard for mobile device", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await contains(".o-mail-PickerContent-picker .o-mail-PickerContent-emojiPicker");
    await click("button", { text: "GIFs" });
    await contains(".popover .o-discuss-GifPicker", { count: 0 });
    await contains(".o-mail-Composer-footer .o-discuss-GifPicker");
});

test("Searching for a GIF with a failling RPC should display an error", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    onRpc("/discuss/gif/categories", () => rpc.categories);
    onRpc("/discuss/gif/search", () => {
        throw new Error("Rpc failed");
    });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='GIFs']");
    await insertText("input[placeholder='Search for a GIF']", "search");
    await contains(".o-discuss-GifPicker-error");
});

test("Scrolling at the bottom should trigger the search to load more gif, even after visiting the favorite.", async () => {
    patchWithCleanup(GifPicker.prototype, {
        get style() {
            return "width: 200px;height: 200px;background: #000";
        },
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    onRpc("/discuss/gif/categories", () => rpc.categories);
    onRpc("/discuss/gif/search", () => {
        const _rpc = rpc.search;
        _rpc.results = gifFactory(4);
        return _rpc;
    });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='GIFs']");
    await click(".o-discuss-GifPicker div[aria-label='list-item']", { text: "Favorites" });
    await click("i[aria-label='back']");
    await click("img[data-src='https://media.tenor.com/6uIlQAHIkNoAAAAM/cry.gif']");
    await contains(".o-discuss-Gif", { count: 4 });
    await scroll(".o-discuss-GifPicker-content", "bottom");
    await contains(".o-discuss-Gif", { count: 8 });
});

test("Show help when no favorite GIF", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    onRpc("/discuss/gif/categories", () => rpc.categories);
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='GIFs']");
    await click(".o-discuss-GifPicker div[aria-label='list-item']", { text: "Favorites" });
    await contains("span", { text: "So uhh... maybe go favorite some GIFs?" });
});
