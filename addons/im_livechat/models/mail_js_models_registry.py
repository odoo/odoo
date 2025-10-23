from odoo.addons.mail.tools.mail_js_models_registry import MODELS_TO_EXPOSE, MODELS_TO_INCLUDE

MODELS_TO_EXPOSE.extend(
    [
        "chatbot.script",
        "chatbot.script.answer",
        "chatbot.script.step",
        "im_livechat.channel",
        "im_livechat.channel.rule",
        "im_livechat.conversation.tag",
        "im_livechat.expertise",
    ]
)
MODELS_TO_INCLUDE.extend(
    [
        "chatbot.script",
        "chatbot.script.answer",
        "chatbot.script.step",
        "im_livechat.channel",
        "im_livechat.channel.rule",
        "im_livechat.conversation.tag",
        "im_livechat.expertise",
    ]
)
