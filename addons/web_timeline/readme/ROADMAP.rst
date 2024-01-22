* Implement a more efficient way of refreshing timeline after a record update;
* Make `attrs` attribute work;
* Make action attributes work (create, edit, delete) like in form and tree views.
* When grouping by m2m and more than one record is set, the timeline item appears only
  on one group. Allow showing in both groups.
* When grouping by m2m and dragging for changing the time or the group, the changes on
  the group will not be set, because it could make disappear the records not related
  with the changes that we want to make. When the item is showed in all groups change
  the value according the group of the dragged item.
