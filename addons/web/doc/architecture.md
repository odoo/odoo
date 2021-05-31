# Architecture

This document explains how the Odoo web client is designed, from a high level
point of view.

## Overview

```
creating an environment => mounting web client
```

## Services

[Services](services/readme.md) are meant to be long lived processes which provides
some features to the web client. They are alive for the duration of the application.
