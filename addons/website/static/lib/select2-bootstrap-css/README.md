CSS for making Select2 fit in with Bootstrap a bit better,  
**updated for Bootstrap v3.0.0**.

http://fk.github.io/select2-bootstrap-css/

Tested with Bootstrap 3.0.0 and Select2 3.3.2, 3.4.1 and 3.4.2 and in latest Chrome, Safari, Firefox, Opera (Mac) and IE8-IE10.

Known issues:

 * "Loading Remote Data" and "Infinite Scroll" not addressed yet, the loading indicator position probably needs some adjustments
 * IE8/IE9/IE10, Firefox: Select2 in "Bootstrap input group with radio/checkbox addon" and .input-lg misses 1px in height (IE9/IE10, Firefox behave the same for Bootstrap 3's "input group sizing"-demo at http://getbootstrap.com/components/#input-groups-sizing)
 * IE9/IE10: Select2 in "Bootstrap input group with button addon" (no height modifier, i. e. .input-sm, .input-lg) also misses 1px in height (bug _not_ inherited from Bootstrap 3)
 * box-shadow for .select2-search input do not fit Bootstrap's defaults
 * the Select2 dropdown could inherit look-and-feel from Bootstrap dropdowns and/or could honor Bootstrap height sizing classes
 * border-radii for opened Select2 dropdowns could consistently be set to be … round ;-)
 * checkboxes and radio-buttons in "Bootstrap input groups" could be vertically aligned to the top (instead of center) if combined with a multi Select2 to address variable height of the Select2 container
