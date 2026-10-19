# Assets

- Every resource a page needs ships in the codebase: copy images, fonts and libraries
  into the addon instead of linking them by URL.
- Third-party libraries go in `static/lib/`, unminified, so they can be read and diffed.
