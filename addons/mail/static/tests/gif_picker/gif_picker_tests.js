/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains, insertText } from "@web/../tests/utils";

const rpc = {
    search: {
        results: [
            {
                id: "16925131306449801434",
                title: "",
                media_formats: {
                    tinygif: {
                        url: "https://media.tenor.com/6uIlQAHIkNoAAAAM/cry.gif",
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
            },
            {
                id: "11429640401266091247",
                title: "",
                media_formats: {
                    tinygif: {
                        url: "https://media.tenor.com/np49Y1vrJO8AAAAM/crying-cry.gif",
                        duration: 0,
                        preview: "",
                        dims: [220, 220],
                        size: 145353,
                    },
                },
                created: 1612455937.558013,
                content_description: "Crying Crying Face GIF",
                itemurl: "https://tenor.com/view/crying-cry-crying-face-gif-20235014",
                url: "https://tenor.com/bw4dm.gif",
                tags: ["crying", "cry", "Crying Face"],
                flags: [],
                hasaudio: false,
            },
        ],
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

QUnit.module("GIF picker");

QUnit.test("composer should display a GIF button", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains("button[aria-label='GIFs']");
});

QUnit.test("Composer GIF button should open the GIF picker", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("button[aria-label='GIFs']");
    await contains(".o-discuss-GifPicker");
});

QUnit.test("Searching for a GIF", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start({
        mockRPC(route) {
            if (route === "/discuss/gif/search") {
                return rpc.search;
            }
        },
    });
    openDiscuss(channelId);
    await click("button[aria-label='GIFs']");
    await insertText("input[placeholder='Search for a GIF']", "search");
    await contains("i[aria-label='back']");
    await contains(".o-discuss-Gif", { count: 2 });
});

QUnit.test("Open a GIF category trigger the search for the category", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start({
        mockRPC(route) {
            if (route === "/discuss/gif/categories") {
                return rpc.categories;
            }
            if (route === "/discuss/gif/search") {
                return rpc.search;
            }
        },
    });
    openDiscuss(channelId);
    await click("button[aria-label='GIFs']");
    await click("img[data-src='https://media.tenor.com/6uIlQAHIkNoAAAAM/cry.gif']");
    await contains(".o-discuss-Gif", { count: 2 });
    await contains("input[placeholder='Search for a GIF']", { value: "cry" });
});

QUnit.test("Reopen GIF category list when going back", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start({
        mockRPC(route) {
            if (route === "/discuss/gif/search") {
                return rpc.search;
            }
            if (route === "/discuss/gif/categories") {
                return rpc.categories;
            }
        },
    });
    openDiscuss(channelId);
    await click("button[aria-label='GIFs']");
    await click("img[data-src='https://media.tenor.com/6uIlQAHIkNoAAAAM/cry.gif']");
    await click("i[aria-label='back']");
    await contains(".o-discuss-GifPicker div[aria-label='list']");
});

QUnit.test("Add GIF to favorite", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start({
        mockRPC(route) {
            if (route === "/discuss/gif/search") {
                return rpc.search;
            }
            if (route === "/discuss/gif/categories") {
                return rpc.categories;
            }
        },
    });
    openDiscuss(channelId);
    await click("button[aria-label='GIFs']");
    await click("img[data-src='https://media.tenor.com/6uIlQAHIkNoAAAAM/cry.gif']");
    await click(":nth-child(1 of div) > .o-discuss-Gif .fa-star-o");
    await contains(".o-discuss-Gif .fa-star");
    await click("i[aria-label='back']");
    await click(".o-discuss-GifPicker div[aria-label='list-item']", { text: "Favorites" });
    await contains(".o-discuss-Gif");
});

QUnit.test("Chatter should not have the GIF button", async () => {
    const { openFormView, pyEnv } = await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    openFormView("res.partner", partnerId);
    await click("button", { text: "Log note" });
    await contains("button[aria-label='GIFs']", { count: 0 });
});

QUnit.test(
    "Composer GIF button should open the GIF picker keyboard for mobile device",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "General" });
        patchUiSize({ size: SIZES.SM });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await click("span", { text: "General" });
        await click("button[aria-label='Emojis']");
        await contains(".o-mail-PickerContent-picker .o-mail-PickerContent-emojiPicker");
        await click("button", { text: "GIFs" });
        await contains(".popover .o-discuss-GifPicker", { count: 0 });
        await contains(".o-mail-Composer-footer .o-discuss-GifPicker");
    }
);

QUnit.test("Searching for a GIF with a failling RPC should display an error", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start({
        mockRPC(route) {
            if (route === "/discuss/gif/search") {
                throw new Error("Rpc failed");
            }
            if (route === "/discuss/gif/categories") {
                return rpc.categories;
            }
        },
    });
    await openDiscuss(channelId);
    await click("button[aria-label='GIFs']");
    await insertText("input[placeholder='Search for a GIF']", "search");
    await contains(".o-discuss-GifPicker-error");
});
