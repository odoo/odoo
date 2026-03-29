# Test

## Technical details

This module does not integrate with an API and, instead, allows for fake payments that can be made
to test applications' payment flows without API credentials nor payment method details.

## Supported features

- Direct payment flow
- Tokenization with our without payment

## Testing instructions

The Test payment acquirer can only be used in test mode.

No payment method details are required and all payments are always successful. If provided, the
"Test Card Information" is used as display name for the created payment tokens.
