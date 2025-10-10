# Models whose definitions should be fetched when building JS model definitions.
# This includes models whose relations need to be preserved in the final output.
MODELS_TO_INCLUDE = [
    "discuss.call.history",
    "discuss.channel",
    "discuss.channel.member",
    "discuss.channel.rtc.session",
    "ir.attachment",
    "mail.activity",
    "mail.activity.type",
    "mail.canned.response",
    "mail.followers",
    "mail.guest",
    "mail.link.preview",
    "mail.message",
    "mail.message.link.preview",
    "mail.message.subtype",
    "mail.notification",
    "mail.scheduled.message",
    "mail.template",
    "mail.thread",
    "res.company",
    "res.country",
    "res.groups",
    "res.groups.privilege",
    "res.lang",
    "res.partner",
    "res.role",
    "res.users",
]

# Models that should actually be included in the "mail.assets_js_model" bundle.
# This allows incremental conversion of JS model definitions to Python definitions,
# so new models can be progressively exposed without fetching everything.
MODELS_TO_EXPOSE = [
    "mail.message",
    "mail.message.link.preview",
]
