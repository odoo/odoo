import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

registry.category("web_tour.tours").add("discuss_channel_as_guest_tour.js", {
    steps: () => [
        {
            content: "Shareable invitation link is shown on welcome page",
            trigger: ".o-mail-WelcomePage",
            run() {
                if (!/^\/chat\/\d+\/[^/]+$/.test(window.location.pathname)) {
                    console.error("Invitation link is not present in URL on welcome page.");
                }
            },
        },
        {
            content: "Fill in guest name",
            trigger: ".o-mail-WelcomePage:has(button[title='Join Channel'])",
            async run({ edit }) {
                if (document.querySelector("input[name='guest_name']")) {
                    await edit("Guest", "input[name='guest_name']");
                }
            },
        },
        {
            content: "Click join",
            trigger: "button[title='Join Channel']:enabled",
            run: "click",
            expectUnloadPage: user.isInternalUser,
        },
        ...(user.isInternalUser
            ? [
                  {
                      content: "Check that the internal user lands in Discuss",
                      trigger: ".o-mail-Discuss .o-mail-Thread",
                      run() {
                          if (!window.location.pathname.startsWith("/odoo/")) {
                              console.error(
                                  "Internal user is not redirected to Discuss after Join."
                              );
                          }
                      },
                  },
              ]
            : [
                  {
                      content: "Check that we are on not in a call",
                      trigger: "button[name='call']",
                  },
                  ...(!user.userId
                      ? [
                            {
                                content:
                                    "Check that a new guest is online, from the websocket opened after Join",
                                trigger:
                                    ".o-discuss-ChannelMember:has(:text(Guest)) .o-mail-ImStatus[title='User is online']",
                            },
                            {
                                trigger:
                                    ".o-mail-PublicSelfMenu-toggler:has(.o-mail-PublicSelfMenu-name:text(Guest))",
                                run: "click",
                            },
                            {
                                content: "Rename the guest from the self menu",
                                trigger: ".o-mail-PublicSelfMenu-guestName",
                                run: "edit Guest Luigi && press Enter",
                            },
                            {
                                trigger:
                                    ".o-mail-PublicSelfMenu-toggler:has(.o-mail-PublicSelfMenu-name:text(Guest Luigi))",
                                run: "click",
                            },
                            {
                                trigger: "body:not(:has(.o-mail-PublicSelfMenu))",
                            },
                        ]
                      : []),
                  {
                      content: "Check that we are on channel page",
                      trigger: ".o-mail-Thread",
                      run: "press ctrl+k",
                  },
                  {
                      trigger: ".o_command_palette_search input",
                      run: "fill @",
                  },
                  {
                      trigger: ".o-mail-DiscussCommand:text(Test channel)",
                  },
              ]),
    ],
});
