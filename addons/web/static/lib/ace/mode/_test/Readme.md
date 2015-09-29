`tokens_<modeName>.json` files keep information about correct tokens and tokenizer states for all modes supported by ace.
They are generated from `text_<modeName>.txt` or `demo/kitchen-sink/doc/*` with

```sh
node highlight_rules_test.js -gen
```

command.

