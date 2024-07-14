# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Retryable error codes
WHATSAPP_RETRYABLE_ERROR_CODES = {
    0,       # We were unable to authenticate the app user.
    1,       # Invalid request or possible server error.
    2,       # Temporary due to downtime or due to being overloaded.
    3,       # Capability or permissions issue.
    4,       # The app has reached its API call rate limit.
    10,      # Permission is either not granted or has been removed.
    33,      # The business phone number has been deleted.
    190,     # Your access token has expired.
    200,     # Permission is either not granted or has been removed.
    299,     # Permission is either not granted or has been removed.
    368,     # The WhatsApp Business Account associated with the app has been restricted or disabled for violating a platform policy.
    80007,   # The WhatsApp Business Account has reached its rate limit.
    130429,  # Cloud API message throughput has been reached.
    131000,  # Message failed to send due to an unknown error.
    131005,  # Permission is either not granted or has been removed.
    131008,  # The request is missing a required parameter.
    131009,  # One or more parameter values are invalid.
    131016,  # A service is temporarily unavailable.
    131042,  # Message failed to send because there were one or more errors related to your payment method.
    131045,  # Message failed to send due to a phone number registration error.
    131048,  # Message failed to send because there are restrictions on how many messages can be sent from this phone number. This may be because too many previous messages were blocked or flagged as spam.
    131052,  # Unable to download the media sent by the user.
    131053,  # Unable to upload the media used in the message.
    131056,  # Too many messages sent from the sender phone number to the same recipient phone number in a short period of time.
    132000,  # The number of variable parameter values included in the request did not match the number of variable parameters defined in the template.
    132001,  # The template does not exist in the specified language or the template has not been approved.
    132012,  # Variable parameter values formatted incorrectly.
    132015,  # Template is paused due to low quality so it cannot be sent in a template message.
    132016,  # Template has been paused too many times due to low quality and is now permanently disabled.
    133004,  # Server is temporarily unavailable.
    133006,  # Phone number needs to be verified before registering.
    133010,  # Phone number not registered on the Whatsapp Business Platform.
}
