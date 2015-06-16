/* The purpose of this script is to copy the current URL of the website
 * into the URL form of the URL shortener (module website_links) 
 * when the user click the link "Share this page" on top of the page.
*/

(function () {
  'use strict';

  $(document).ready(function () {
    $('#o_website_links_share_page').attr('href', '/r?u=' + encodeURIComponent(window.location.href));
  });
})();
