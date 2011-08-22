/*
 strftime for Javascript
 Copyright (c) 2008, Philip S Tellis <philip@bluesmoon.info>
 All rights reserved.
 
 This code is distributed under the terms of the BSD licence
 
 Redistribution and use of this software in source and binary forms, with or without modification,
 are permitted provided that the following conditions are met:

   * Redistributions of source code must retain the above copyright notice, this list of conditions
     and the following disclaimer.
   * Redistributions in binary form must reproduce the above copyright notice, this list of
     conditions and the following disclaimer in the documentation and/or other materials provided
     with the distribution.
   * The names of the contributors to this file may not be used to endorse or promote products
     derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

/**
 * \file strftime.js
 * \author Philip S Tellis \<philip@bluesmoon.info\>
 * \version 1.3
 * \date 2008/06
 * \brief Javascript implementation of strftime
 * 
 * Implements strftime for the Date object in javascript based on the PHP implementation described at
 * http://www.php.net/strftime  This is in turn based on the Open Group specification defined
 * at http://www.opengroup.org/onlinepubs/007908799/xsh/strftime.html This implementation does not
 * include modified conversion specifiers (i.e., Ex and Ox)
 *
 * The following format specifiers are supported:
 *
 * \copydoc formats
 *
 * \%a, \%A, \%b and \%B should be localised for non-English locales.
 *
 * \par Usage:
 * This library may be used as follows:
 * \code
 *     var d = new Date();
 *
 *     var ymd = d.strftime('%Y/%m/%d');
 *     var iso = d.strftime('%Y-%m-%dT%H:%M:%S%z');
 *
 * \endcode
 *
 * \sa \link Date.prototype.strftime Date.strftime \endlink for a description of each of the supported format specifiers
 * \sa Date.ext.locales for localisation information
 * \sa http://www.php.net/strftime for the PHP implementation which is the basis for this
 * \sa http://tech.bluesmoon.info/2008/04/strftime-in-javascript.html for feedback
 */

//! Date extension object - all supporting objects go in here.
Date.ext = {};

//! Utility methods
Date.ext.util = {};

/**
\brief Left pad a number with something
\details Takes a number and pads it to the left with the passed in pad character
\param x	The number to pad
\param pad	The string to pad with
\param r	[optional] Upper limit for pad.  A value of 10 pads to 2 digits, a value of 100 pads to 3 digits.
		Default is 10.

\return The number left padded with the pad character.  This function returns a string and not a number.
*/
Date.ext.util.xPad=function(x, pad, r)
{
	if(typeof(r) == 'undefined')
	{
		r=10;
	}
	for( ; parseInt(x, 10)<r && r>1; r/=10)
		x = pad.toString() + x;
	return x.toString();
};

/**
\brief Currently selected locale.
\details
The locale for a specific date object may be changed using \code Date.locale = "new-locale"; \endcode
The default will be based on the lang attribute of the HTML tag of your document
*/
Date.prototype.locale = 'en-GB';
//! \cond FALSE
if(document.getElementsByTagName('html') && document.getElementsByTagName('html')[0].lang)
{
	Date.prototype.locale = document.getElementsByTagName('html')[0].lang;
}
//! \endcond

/**
\brief Localised strings for days of the week and months of the year.
\details
To create your own local strings, add a locale object to the locales object.
The key of your object should be the same as your locale name.  For example:
   en-US,
   fr,
   fr-CH,
   de-DE
Names are case sensitive and are described at http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
Your locale object must contain the following keys:
\param a	Short names of days of week starting with Sunday
\param A	Long names days of week starting with Sunday
\param b	Short names of months of the year starting with January
\param B	Long names of months of the year starting with February
\param c	The preferred date and time representation in your locale
\param p	AM or PM in your locale
\param P	am or pm in your locale
\param x	The  preferred date representation for the current locale without the time.
\param X	The preferred time representation for the current locale without the date.

\sa Date.ext.locales.en for a sample implementation
\sa \ref localisation for detailed documentation on localising strftime for your own locale
*/
Date.ext.locales = { };

/**
 * \brief Localised strings for English (British).
 * \details
 * This will be used for any of the English dialects unless overridden by a country specific one.
 * This is the default locale if none specified
 */
Date.ext.locales.en = {
	a: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
	A: ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
	b: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
	B: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
	c: '%a %d %b %Y %T %Z',
	p: ['AM', 'PM'],
	P: ['am', 'pm'],
	x: '%d/%m/%y',
	X: '%T'
};

//! \cond FALSE
// Localised strings for US English
Date.ext.locales['en-US'] = Date.ext.locales.en;
Date.ext.locales['en-US'].c = '%a %d %b %Y %r %Z';
Date.ext.locales['en-US'].x = '%D';
Date.ext.locales['en-US'].X = '%r';

// Localised strings for British English
Date.ext.locales['en-GB'] = Date.ext.locales.en;

// Localised strings for Australian English
Date.ext.locales['en-AU'] = Date.ext.locales['en-GB'];
//! \endcond

//! \brief List of supported format specifiers.
/**
 * \details
 * \arg \%a - abbreviated weekday name according to the current locale
 * \arg \%A - full weekday name according to the current locale
 * \arg \%b - abbreviated month name according to the current locale
 * \arg \%B - full month name according to the current locale
 * \arg \%c - preferred date and time representation for the current locale
 * \arg \%C - century number (the year divided by 100 and truncated to an integer, range 00 to 99)
 * \arg \%d - day of the month as a decimal number (range 01 to 31)
 * \arg \%D - same as %m/%d/%y
 * \arg \%e - day of the month as a decimal number, a single digit is preceded by a space (range ' 1' to '31')
 * \arg \%g - like %G, but without the century
 * \arg \%G - The 4-digit year corresponding to the ISO week number
 * \arg \%h - same as %b
 * \arg \%H - hour as a decimal number using a 24-hour clock (range 00 to 23)
 * \arg \%I - hour as a decimal number using a 12-hour clock (range 01 to 12)
 * \arg \%j - day of the year as a decimal number (range 001 to 366)
 * \arg \%m - month as a decimal number (range 01 to 12)
 * \arg \%M - minute as a decimal number
 * \arg \%n - newline character
 * \arg \%p - either `AM' or `PM' according to the given time value, or the corresponding strings for the current locale
 * \arg \%P - like %p, but lower case
 * \arg \%r - time in a.m. and p.m. notation equal to %I:%M:%S %p
 * \arg \%R - time in 24 hour notation equal to %H:%M
 * \arg \%S - second as a decimal number
 * \arg \%t - tab character
 * \arg \%T - current time, equal to %H:%M:%S
 * \arg \%u - weekday as a decimal number [1,7], with 1 representing Monday
 * \arg \%U - week number of the current year as a decimal number, starting with
 *            the first Sunday as the first day of the first week
 * \arg \%V - The ISO 8601:1988 week number of the current year as a decimal number,
 *            range 01 to 53, where week 1 is the first week that has at least 4 days
 *            in the current year, and with Monday as the first day of the week.
 * \arg \%w - day of the week as a decimal, Sunday being 0
 * \arg \%W - week number of the current year as a decimal number, starting with the
 *            first Monday as the first day of the first week
 * \arg \%x - preferred date representation for the current locale without the time
 * \arg \%X - preferred time representation for the current locale without the date
 * \arg \%y - year as a decimal number without a century (range 00 to 99)
 * \arg \%Y - year as a decimal number including the century
 * \arg \%z - numerical time zone representation
 * \arg \%Z - time zone name or abbreviation
 * \arg \%% - a literal `\%' character
 */
Date.ext.formats = {
	a: function(d) { return Date.ext.locales[d.locale].a[d.getDay()]; },
	A: function(d) { return Date.ext.locales[d.locale].A[d.getDay()]; },
	b: function(d) { return Date.ext.locales[d.locale].b[d.getMonth()]; },
	B: function(d) { return Date.ext.locales[d.locale].B[d.getMonth()]; },
	c: 'toLocaleString',
	C: function(d) { return Date.ext.util.xPad(parseInt(d.getFullYear()/100, 10), 0); },
	d: ['getDate', '0'],
	e: ['getDate', ' '],
	g: function(d) { return Date.ext.util.xPad(parseInt(Date.ext.util.G(d)/100, 10), 0); },
	G: function(d) {
			var y = d.getFullYear();
			var V = parseInt(Date.ext.formats.V(d), 10);
			var W = parseInt(Date.ext.formats.W(d), 10);

			if(W > V) {
				y++;
			} else if(W===0 && V>=52) {
				y--;
			}

			return y;
		},
	H: ['getHours', '0'],
	I: function(d) { var I=d.getHours()%12; return Date.ext.util.xPad(I===0?12:I, 0); },
	j: function(d) {
			var ms = d - new Date('' + d.getFullYear() + '/1/1 GMT');
			ms += d.getTimezoneOffset()*60000;
			var doy = parseInt(ms/60000/60/24, 10)+1;
			return Date.ext.util.xPad(doy, 0, 100);
		},
	m: function(d) { return Date.ext.util.xPad(d.getMonth()+1, 0); },
	M: ['getMinutes', '0'],
	p: function(d) { return Date.ext.locales[d.locale].p[d.getHours() >= 12 ? 1 : 0 ]; },
	P: function(d) { return Date.ext.locales[d.locale].P[d.getHours() >= 12 ? 1 : 0 ]; },
	S: ['getSeconds', '0'],
	u: function(d) { var dow = d.getDay(); return dow===0?7:dow; },
	U: function(d) {
			var doy = parseInt(Date.ext.formats.j(d), 10);
			var rdow = 6-d.getDay();
			var woy = parseInt((doy+rdow)/7, 10);
			return Date.ext.util.xPad(woy, 0);
		},
	V: function(d) {
			var woy = parseInt(Date.ext.formats.W(d), 10);
			var dow1_1 = (new Date('' + d.getFullYear() + '/1/1')).getDay();
			// First week is 01 and not 00 as in the case of %U and %W,
			// so we add 1 to the final result except if day 1 of the year
			// is a Monday (then %W returns 01).
			// We also need to subtract 1 if the day 1 of the year is 
			// Friday-Sunday, so the resulting equation becomes:
			var idow = woy + (dow1_1 > 4 || dow1_1 <= 1 ? 0 : 1);
			if(idow == 53 && (new Date('' + d.getFullYear() + '/12/31')).getDay() < 4)
			{
				idow = 1;
			}
			else if(idow === 0)
			{
				idow = Date.ext.formats.V(new Date('' + (d.getFullYear()-1) + '/12/31'));
			}

			return Date.ext.util.xPad(idow, 0);
		},
	w: 'getDay',
	W: function(d) {
			var doy = parseInt(Date.ext.formats.j(d), 10);
			var rdow = 7-Date.ext.formats.u(d);
			var woy = parseInt((doy+rdow)/7, 10);
			return Date.ext.util.xPad(woy, 0, 10);
		},
	y: function(d) { return Date.ext.util.xPad(d.getFullYear()%100, 0); },
	Y: 'getFullYear',
	z: function(d) {
			var o = d.getTimezoneOffset();
			var H = Date.ext.util.xPad(parseInt(Math.abs(o/60), 10), 0);
			var M = Date.ext.util.xPad(o%60, 0);
			return (o>0?'-':'+') + H + M;
		},
	Z: function(d) { return d.toString().replace(/^.*\(([^)]+)\)$/, '$1'); },
	'%': function(d) { return '%'; }
};

/**
\brief List of aggregate format specifiers.
\details
Aggregate format specifiers map to a combination of basic format specifiers.
These are implemented in terms of Date.ext.formats.

A format specifier that maps to 'locale' is read from Date.ext.locales[current-locale].

\sa Date.ext.formats
*/
Date.ext.aggregates = {
	c: 'locale',
	D: '%m/%d/%y',
	h: '%b',
	n: '\n',
	r: '%I:%M:%S %p',
	R: '%H:%M',
	t: '\t',
	T: '%H:%M:%S',
	x: 'locale',
	X: 'locale'
};

//! \cond FALSE
// Cache timezone values because they will never change for a given JS instance
Date.ext.aggregates.z = Date.ext.formats.z(new Date());
Date.ext.aggregates.Z = Date.ext.formats.Z(new Date());
//! \endcond

//! List of unsupported format specifiers.
/**
 * \details
 * All format specifiers supported by the PHP implementation are supported by
 * this javascript implementation.
 */
Date.ext.unsupported = { };


/**
 * \brief Formats the date according to the specified format.
 * \param fmt	The format to format the date in.  This may be a combination of the following:
 * \copydoc formats
 *
 * \return	A string representation of the date formatted based on the passed in parameter
 * \sa http://www.php.net/strftime for documentation on format specifiers
*/
Date.prototype.strftime=function(fmt)
{
	// Fix locale if declared locale hasn't been defined
	// After the first call this condition should never be entered unless someone changes the locale
	if(!(this.locale in Date.ext.locales))
	{
		if(this.locale.replace(/-[a-zA-Z]+$/, '') in Date.ext.locales)
		{
			this.locale = this.locale.replace(/-[a-zA-Z]+$/, '');
		}
		else
		{
			this.locale = 'en-GB';
		}
	}

	var d = this;
	// First replace aggregates
	while(fmt.match(/%[cDhnrRtTxXzZ]/))
	{
		fmt = fmt.replace(/%([cDhnrRtTxXzZ])/g, function(m0, m1)
				{
					var f = Date.ext.aggregates[m1];
					return (f == 'locale' ? Date.ext.locales[d.locale][m1] : f);
				});
	}


	// Now replace formats - we need a closure so that the date object gets passed through
	var str = fmt.replace(/%([aAbBCdegGHIjmMpPSuUVwWyY%])/g, function(m0, m1) 
			{
				var f = Date.ext.formats[m1];
				if(typeof(f) == 'string') {
					return d[f]();
				} else if(typeof(f) == 'function') {
					return f.call(d, d);
				} else if(typeof(f) == 'object' && typeof(f[0]) == 'string') {
					return Date.ext.util.xPad(d[f[0]](), f[1]);
				} else {
					return m1;
				}
			});
	d=null;
	return str;
};

/**
 * \mainpage strftime for Javascript
 *
 * \section toc Table of Contents
 * - \ref intro_sec
 * - <a class="el" href="strftime.js">Download full source</a> / <a class="el" href="strftime-min.js">minified</a>
 * - \subpage usage
 * - \subpage format_specifiers
 * - \subpage localisation
 * - \link strftime.js API Documentation \endlink
 * - \subpage demo
 * - \subpage changelog
 * - \subpage faq
 * - <a class="el" href="http://tech.bluesmoon.info/2008/04/strftime-in-javascript.html">Feedback</a>
 * - \subpage copyright_licence
 *
 * \section intro_sec Introduction
 *
 * C and PHP developers have had access to a built in strftime function for a long time.
 * This function is an easy way to format dates and times for various display needs.
 *
 * This library brings the flexibility of strftime to the javascript Date object
 *
 * Use this library if you frequently need to format dates in javascript in a variety of ways.  For example,
 * if you have PHP code that writes out formatted dates, and want to mimic the functionality using
 * progressively enhanced javascript, then this library can do exactly what you want.
 *
 *
 *
 *
 * \page usage Example usage
 *
 * \section usage_sec Usage
 * This library may be used as follows:
 * \code
 *     var d = new Date();
 *
 *     var ymd = d.strftime('%Y/%m/%d');
 *     var iso = d.strftime('%Y-%m-%dT%H:%M:%S%z');
 *
 * \endcode
 *
 * \subsection examples Examples
 * 
 * To get the current time in hours and minutes:
 * \code
 * 	var d = new Date();
 * 	d.strftime("%H:%M");
 * \endcode
 *
 * To get the current time with seconds in AM/PM notation:
 * \code
 * 	var d = new Date();
 * 	d.strftime("%r");
 * \endcode
 *
 * To get the year and day of the year for August 23, 2009:
 * \code
 * 	var d = new Date('2009/8/23');
 * 	d.strftime("%Y-%j");
 * \endcode
 *
 * \section demo_sec Demo
 *
 * Try your own examples on the \subpage demo page.  You can use any of the supported
 * \subpage format_specifiers.
 *
 *
 *
 *
 * \page localisation Localisation
 * You can localise strftime by implementing the short and long forms for days of the
 * week and months of the year, and the localised aggregates for the preferred date
 * and time representation for your locale.  You need to add your locale to the
 * Date.ext.locales object.
 *
 * \section localising_fr Localising for french
 *
 * For example, this is how we'd add French language strings to the locales object:
 * \dontinclude index.html
 * \skip Generic french
 * \until };
 * The % format specifiers are all defined in \ref formats.  You can use any of those.
 *
 * This locale definition may be included in your own source file, or in the HTML file
 * including \c strftime.js, however it must be defined \em after including \c strftime.js
 *
 * The above definition includes generic french strings and formats that are used in France.
 * Other french speaking countries may have other representations for dates and times, so we
 * need to override this for them.  For example, Canadian french uses a Y-m-d date format,
 * while French french uses d.m.Y.  We fix this by defining Canadian french to be the same
 * as generic french, and then override the format specifiers for \c x for the \c fr-CA locale:
 * \until End french
 *
 * You can now use any of the French locales at any time by setting \link Date.prototype.locale Date.locale \endlink
 * to \c "fr", \c "fr-FR", \c "fr-CA", or any other french dialect:
 * \code
 *     var d = new Date("2008/04/22");
 *     d.locale = "fr";
 *
 *     d.strftime("%A, %d %B == %x");
 * \endcode
 * will return:
 * \code
 *     mardi, 22 avril == 22.04.2008
 * \endcode
 * While changing the locale to "fr-CA":
 * \code
 *     d.locale = "fr-CA";
 *
 *     d.strftime("%A, %d %B == %x");
 * \endcode
 * will return:
 * \code
 *     mardi, 22 avril == 2008-04-22
 * \endcode
 *
 * You can use any of the format specifiers defined at \ref formats
 *
 * The locale for all dates defaults to the value of the \c lang attribute of your HTML document if
 * it is set, or to \c "en" otherwise.
 * \note
 * Your locale definitions \b MUST be added to the locale object before calling
 * \link Date.prototype.strftime Date.strftime \endlink.
 *
 * \sa \ref formats for a list of format specifiers that can be used in your definitions
 * for c, x and X.
 *
 * \section locale_names Locale names
 *
 * Locale names are defined in RFC 1766. Typically, a locale would be a two letter ISO639
 * defined language code and an optional ISO3166 defined country code separated by a -
 * 
 * eg: fr-FR, de-DE, hi-IN
 *
 * \sa http://www.ietf.org/rfc/rfc1766.txt
 * \sa http://www.loc.gov/standards/iso639-2/php/code_list.php
 * \sa http://www.iso.org/iso/country_codes/iso_3166_code_lists/english_country_names_and_code_elements.htm
 * 
 * \section locale_fallback Locale fallbacks
 *
 * If a locale object corresponding to the fully specified locale isn't found, an attempt will be made
 * to fall back to the two letter language code.  If a locale object corresponding to that isn't found
 * either, then the locale will fall back to \c "en".  No warning will be issued.
 *
 * For example, if we define a locale for de:
 * \until };
 * Then set the locale to \c "de-DE":
 * \code
 *     d.locale = "de-DE";
 *
 *     d.strftime("%a, %d %b");
 * \endcode
 * In this case, the \c "de" locale will be used since \c "de-DE" has not been defined:
 * \code
 *     Di, 22 Apr
 * \endcode
 *
 * Swiss german will return the same since it will also fall back to \c "de":
 * \code
 *     d.locale = "de-CH";
 *
 *     d.strftime("%a, %d %b");
 * \endcode
 * \code
 *     Di, 22 Apr
 * \endcode
 *
 * We need to override the \c a specifier for Swiss german, since it's different from German german:
 * \until End german
 * We now get the correct results:
 * \code
 *     d.locale = "de-CH";
 *
 *     d.strftime("%a, %d %b");
 * \endcode
 * \code
 *     Die, 22 Apr
 * \endcode
 *
 * \section builtin_locales Built in locales
 *
 * This library comes with pre-defined locales for en, en-GB, en-US and en-AU.
 *
 * 
 *
 *
 * \page format_specifiers Format specifiers
 * 
 * \section specifiers Format specifiers
 * strftime has several format specifiers defined by the Open group at 
 * http://www.opengroup.org/onlinepubs/007908799/xsh/strftime.html
 *
 * PHP added a few of its own, defined at http://www.php.net/strftime
 *
 * This javascript implementation supports all the PHP specifiers
 *
 * \subsection supp Supported format specifiers:
 * \copydoc formats
 * 
 * \subsection unsupportedformats Unsupported format specifiers:
 * \copydoc unsupported
 *
 *
 *
 *
 * \page demo strftime demo
 * <div style="float:right;width:45%;">
 * \copydoc formats
 * </div>
 * \htmlinclude index.html
 *
 *
 *
 *
 * \page faq FAQ
 * 
 * \section how_tos Usage
 *
 * \subsection howtouse Is there a manual on how to use this library?
 *
 * Yes, see \ref usage
 *
 * \subsection wheretoget Where can I get a minified version of this library?
 *
 * The minified version is available <a href="strftime-min.js" title="Minified strftime.js">here</a>.
 *
 * \subsection which_specifiers Which format specifiers are supported?
 *
 * See \ref format_specifiers
 *
 * \section whys Why?
 *
 * \subsection why_lib Why this library?
 *
 * I've used the strftime function in C, PHP and the Unix shell, and found it very useful
 * to do date formatting.  When I needed to do date formatting in javascript, I decided
 * that it made the most sense to just reuse what I'm already familiar with.
 *
 * \subsection why_another Why another strftime implementation for Javascript?
 *
 * Yes, there are other strftime implementations for Javascript, but I saw problems with
 * all of them that meant I couldn't use them directly.  Some implementations had bad
 * designs.  For example, iterating through all possible specifiers and scanning the string
 * for them.  Others were tied to specific libraries like prototype.
 *
 * Trying to extend any of the existing implementations would have required only slightly
 * less effort than writing this from scratch.  In the end it took me just about 3 hours
 * to write the code and about 6 hours battling with doxygen to write these docs.
 *
 * I also had an idea of how I wanted to implement this, so decided to try it.
 *
 * \subsection why_extend_date Why extend the Date class rather than subclass it?
 *
 * I tried subclassing Date and failed.  I didn't want to waste time on figuring
 * out if there was a problem in my code or if it just wasn't possible.  Adding to the
 * Date.prototype worked well, so I stuck with it.
 *
 * I did have some worries because of the way for..in loops got messed up after json.js added
 * to the Object.prototype, but that isn't an issue here since {} is not a subclass of Date.
 *
 * My last doubt was about the Date.ext namespace that I created.  I still don't like this,
 * but I felt that \c ext at least makes clear that this is external or an extension.
 *
 * It's quite possible that some future version of javascript will add an \c ext or a \c locale
 * or a \c strftime property/method to the Date class, but this library should probably
 * check for capabilities before doing what it does.
 *
 * \section curiosity Curiosity
 *
 * \subsection how_big How big is the code?
 *
 * \arg 26K bytes with documentation
 * \arg 4242 bytes minified using <a href="http://developer.yahoo.com/yui/compressor/">YUI Compressor</a>
 * \arg 1477 bytes minified and gzipped
 *
 * \subsection how_long How long did it take to write this?
 *
 * 15 minutes for the idea while I was composing this blog post:
 * http://tech.bluesmoon.info/2008/04/javascript-date-functions.html
 *
 * 3 hours in one evening to write v1.0 of the code and 6 hours the same
 * night to write the docs and this manual.  As you can tell, I'm fairly
 * sleepy.
 *
 * Versions 1.1 and 1.2 were done in a couple of hours each, and version 1.3
 * in under one hour.
 *
 * \section contributing Contributing
 *
 * \subsection how_to_rfe How can I request features or make suggestions?
 *
 * You can leave a comment on my blog post about this library here:
 * http://tech.bluesmoon.info/2008/04/strftime-in-javascript.html
 *
 * \subsection how_to_contribute Can I/How can I contribute code to this library?
 *
 * Yes, that would be very nice, thank you.  You can do various things.  You can make changes
 * to the library, and make a diff against the current file and mail me that diff at
 * philip@bluesmoon.info, or you could just host the new file on your own servers and add
 * your name to the copyright list at the top stating which parts you've added.
 *
 * If you do mail me a diff, let me know how you'd like to be listed in the copyright section.
 *
 * \subsection copyright_signover Who owns the copyright on contributed code?
 *
 * The contributor retains copyright on contributed code.
 *
 * In some cases I may use contributed code as a template and write the code myself.  In this
 * case I'll give the contributor credit for the idea, but will not add their name to the
 * copyright holders list.
 *
 *
 *
 *
 * \page copyright_licence Copyright & Licence
 *
 * \section copyright Copyright
 * \dontinclude strftime.js
 * \skip Copyright
 * \until rights
 *
 * \section licence Licence
 * \skip This code
 * \until SUCH DAMAGE.
 *
 *
 *
 * \page changelog ChangeLog
 *
 * \par 1.3 - 2008/06/17:
 * - Fixed padding issue with negative timezone offsets in %r
 *   reported and fixed by Mikko <mikko.heimola@iki.fi>
 * - Added support for %P
 * - Internationalised %r, %p and %P
 *
 * \par 1.2 - 2008/04/27:
 * - Fixed support for c (previously it just returned toLocaleString())
 * - Add support for c, x and X
 * - Add locales for en-GB, en-US and en-AU
 * - Make en-GB the default locale (previous was en)
 * - Added more localisation docs
 *
 * \par 1.1 - 2008/04/27:
 * - Fix bug in xPad which wasn't padding more than a single digit
 * - Fix bug in j which had an off by one error for days after March 10th because of daylight savings
 * - Add support for g, G, U, V and W
 *
 * \par 1.0 - 2008/04/22:
 * - Initial release with support for a, A, b, B, c, C, d, D, e, H, I, j, m, M, p, r, R, S, t, T, u, w, y, Y, z, Z, and %
 */
