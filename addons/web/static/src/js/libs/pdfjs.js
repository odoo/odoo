/*
* There is no changes to pdf.js in this file, but only a note about a change that has been done in it.
*
* In the module account_invoice_extract, the the code need to react to the 'pagerendered' event triggered by
* pdf.js. However in recent version of pdf.js, event are not visible outside of the library, except if the 
* 'eventBusDispatchToDOM' has been set to true.
*
* We tried to set this option from outside of the library but without success, as our pdf viewer is in an iframe.
* There is no state of the iframe in which we can add an event listener to set the option.
* pdf.js has an event used to signal when we can set settings, called 'webviewerloaded'.
* This event is triggered in an EventListener attached to the 'DOMContentLoaded' event.
* So, to list options we had, we could:
* a) add an eventListener to the iframe document or window to react to 'webviewerloaded'. This doesn't work as 
*    document and windows are not the definitive ones and won't catche the event later.
* b) add an eventListener to the iframe to react to 'DOMContentLoaded', which doens't work too as our listener will be called
*    after the pdf.js one.
*
* Finally the option was choosed to modify the default value of this option directly in pdf.js as no hook worked in the
* 'account_invoice_extract' module.
*/
