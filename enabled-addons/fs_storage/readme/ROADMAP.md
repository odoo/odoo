- Transactions: fsspec comes with a transactional mechanism that once
  started, gathers all the files created during the transaction, and if
  the transaction is committed, moves them to their final locations. It
  would be useful to bridge this with the transactional mechanism of
  odoo. This would allow to ensure that all the files created during a
  transaction are either all moved to their final locations, or all
  deleted if the transaction is rolled back. This mechanism is only
  valid for files created during the transaction by a call to the open
  method of the file system. It is not valid for others operations, such
  as rm, mv_file, ... .
