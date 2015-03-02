Contributing to Select2
=======================
Looking to contribute something to Select2? **Here's how you can help.**

Please take a moment to review this document in order to make the contribution
process easy and effective for everyone involved.

Following these guidelines helps to communicate that you respect the time of
the developers managing and developing this open source project. In return,
they should reciprocate that respect in addressing your issue or assessing
patches and features.

Using the issue tracker
-----------------------
When [reporting bugs][reporting-bugs] or
[requesting features][requesting-features], the
[issue tracker on GitHub][issue-tracker] is the recommended channel to use.

The issue tracker **is not** a place for support requests. The
[mailing list][mailing-list] or [IRC channel][irc-channel] are better places to
get help.

Reporting bugs with Select2
---------------------------
We really appreciate clear bug reports that _consistently_ show an issue
_within Select2_.

The ideal bug report follows these guidelines:

1. **Use the [GitHub issue search][issue-search]**  &mdash; Check if the issue
   has already been reported.
2. **Check if the issue has been fixed**  &mdash; Try to reproduce the problem
   using the code in the `master` branch.
3. **Isolate the problem**  &mdash; Try to create an
   [isolated test case][isolated-case] that consistently reproduces the problem.

Please try to be as detailed as possible in your bug report, especially if an
isolated test case cannot be made. Some useful questions to include the answer
to are:

- What steps can be used to reproduce the issue?
- What is the bug and what is the expected outcome?
- What browser(s) and Operating System have you tested with?
- Does the bug happen consistently across all tested browsers?
- What version of jQuery are you using? And what version of Select2?
- Are you using Select2 with other plugins?

All of these questions will help people fix and identify any potential bugs.

Requesting features in Select2
------------------------------
Select2 is a large library that carries with it a lot of functionality. Because
of this, many feature requests will not be implemented in the core library.

Before starting work on a major feature for Select2, **contact the
[community][community] first** or you may risk spending a considerable amount of
time on something which the project developers are not interested in bringing
into the project.

### Select2 4.0

Many feature requests will be closed off until 4.0, where Select2 plans to adopt
a more flexible API.  If you are interested in helping with the development of
the next major Select2 release, please send a message to the
[mailing list][mailing-list] or [irc channel][irc-channel] for more information.

Triaging issues and pull requests
---------------------------------
Anyone can help the project maintainers triage issues and review pull requests.

### Handling new issues

Select2 regularly receives new issues which need to be tested and organized.

When a new issue that comes in that is similar to another existing issue, it
should be checked to make sure it is not a duplicate.  Duplicates issues should
be marked by replying to the issue with "Duplicate of #[issue number]" where
`[issue number]` is the url or issue number for the existing issue.  This will
allow the project maintainers to quickly close off additional issues and keep
the discussion focused within a single issue.

If you can test issues that are reported to Select2 that contain test cases and
confirm under what conditions bugs happen, that will allow others to identify
what causes a bug quicker.

### Reviewing pull requests

It is very common for pull requests to be opened for issues that contain a clear
solution to the problem.  These pull requests should be rigorously reviewed by
the community before being accepted.  If you are not sure about a piece of
submitted code, or know of a better way to do something, do not hesitate to make
a comment on the pull request.

It should also be made clear that **all code contributed to Select** must be
licensable under the [Apache 2 or GPL 2 licenses][licensing].  Code that cannot
be released under either of these licenses **cannot be accepted** into the
project.

[community]: https://github.com/ivaynberg/select2#community
[reporting-bugs]: #reporting-bugs-with-select2
[requesting-features]: #requesting-features-in-select2
[issue-tracker]: https://github.com/ivaynberg/select2/issues
[mailing-list]: https://github.com/ivaynberg/select2#mailing-list
[irc-channel]: https://github.com/ivaynberg/select2#irc-channel
[issue-search]: https://github.com/ivaynberg/select2/search?q=&type=Issues
[isolated-case]: http://css-tricks.com/6263-reduced-test-cases/
[licensing]: https://github.com/ivaynberg/select2#copyright-and-license
