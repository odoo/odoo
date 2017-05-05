.. _roadmap:

#######
Roadmap
#######

Here is a list of things we may agree to merge.

* Queue: use PostgreSQL `notify` for direct enqueue of jobs

  See: https://github.com/OCA/connector/pull/52

* Add facilities to parse the errors from the jobs so we can replace it
  by more contextual and helpful errors.

* A logger which keeps in a buffer all the logs and flushes them when an error
  occurs in a synchronization, clears them if it succeeded

* Job Channels: each job is owned by a channel and workers can be
  dedicated to one channel only

  See: https://github.com/OCA/connector/pull/52
