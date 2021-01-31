/*
Copyright (c) 2008-2012 NaN Projectes de Programari Lliure, S.L.
                        http://www.NaN-tic.com

WARNING: This program as such is intended to be used by professional
programmers who take the whole responsability of assessing all potential
consequences resulting from its eventual inadequacies and bugs
End users who are looking for a ready-to-use solution with commercial
garantees and support are strongly adviced to contract a Free Software
Service Company

This program is Free Software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
*/
package com.nantic.jasperreports;

import java.io.FileInputStream;
import java.util.PropertyResourceBundle;
import java.util.Hashtable;
import java.util.Map;
import java.util.Locale;
import java.util.ResourceBundle;
import java.util.Enumeration;

import org.xnap.commons.i18n.I18n;

public class Translator {
    private Hashtable<Locale, I18n> resources = null;
    private String baseName = null;
    private Locale defaultLocale = null;
    private Hashtable<Locale, Boolean> unavailableResources = null;

    public Translator(String baseName, Locale defaultLocale) {
        resources = new Hashtable<Locale, I18n>();
        this.baseName = baseName;
        this.defaultLocale = defaultLocale;
        unavailableResources = new Hashtable<Locale, Boolean>();
    }
    /* Ensures the given locale is loaded */
    protected boolean loadLocale( Locale locale ) {
        // If the resource wasn't available don't try to load it each time.
        if ( baseName == null || locale == null )
            return false;
        if ( unavailableResources.containsKey( locale ) )
            return false;
        if ( ! resources.containsKey( locale ) ) {
            
            String fileName = baseName + "_" + locale.toString() + ".properties";
            ResourceBundle bundle; 
            try {
                FileInputStream fis = new FileInputStream( fileName );
                bundle = new PropertyResourceBundle(fis);
                resources.put( locale, new I18n( bundle ) );
            } catch (Exception e) {
                //e.printStackTrace();
                unavailableResources.put( locale, true );
                System.out.println( "JasperServer: No bundle file named: " + fileName );
                return false;
            }
        }
        return true;
    }
    public Locale stringToLocale(String localeCode) {
        Locale locale;
        String[] locales = localeCode.split( "_" );
        if ( locales.length == 1 )
            locale = new Locale( locales[0] );
        else if ( locales.length == 2 )
            locale = new Locale( locales[0], locales[1] );
        else
            locale = new Locale( locales[0], locales[1], locales[2] );
        return locale;
    }
    /* tr(Locale..) and tr(Locale..Object) functions */
    public String tr(Locale locale, String text) {
        if ( ! loadLocale( locale ) ) {
            return text;
        }
        return resources.get( locale ).tr( text );
    }
    public String tr(Locale locale, String text, Object o) {
        if ( ! loadLocale( locale ) )
            return text;
        return resources.get( locale ).tr( text, o );
    }
    public String tr(Locale locale, String text, Object o1, Object o2) {
        if ( ! loadLocale( locale ) )
            return text;
        return resources.get( locale ).tr( text, o1, o2 );
    }
    public String tr(Locale locale, String text, Object o1, Object o2, Object o3) {
        if ( ! loadLocale( locale ) )
            return text;
        return resources.get( locale ).tr( text, o1, o2, o3 );
    }
    public String tr(Locale locale, String text, Object o1, Object o2, Object o3, Object o4) {
        if ( ! loadLocale( locale ) )
            return text;
        return resources.get( locale ).tr( text, o1, o2, o3, o4 );
    }
    public String tr(Locale locale, String text, Object[] objects) {
        if ( ! loadLocale( locale ) )
            return text;
        return resources.get( locale ).tr( text, objects );
    }
    /* trl() and trl(..Object) functions */
    public String trl(String localeCode, String text) {
        return tr(stringToLocale(localeCode), text);
    }
    public String trl(String localeCode, String text, Object o) {
        return tr(stringToLocale(localeCode), text, o);
    }
    public String trl(String localeCode, String text, Object o1, Object o2) {
        return tr(stringToLocale(localeCode), text, o1, o2);
    }
    public String trl(String localeCode, String text, Object o1, Object o2, Object o3) {
        return tr(stringToLocale(localeCode), text, o1, o2, o3);
    }
    public String trl(String localeCode, String text, Object o1, Object o2, Object o3, Object o4) {
        return tr(stringToLocale(localeCode), text, o1, o2, o3, o4);
    }
    public String trl(String localeCode, String text, Object[] objects) {
        return tr(stringToLocale(localeCode), text, objects);
    }
    /* tr(..) and tr(..Object) functions */
    public String tr(String text) {
        return tr(defaultLocale, text);
    }
    public String tr(String text, Object o) {
        return tr(defaultLocale, text, o);
    }
    public String tr(String text, Object o1, Object o2) {
        return tr(defaultLocale, text, o1, o2);
    }
    public String tr(String text, Object o1, Object o2, Object o3) {
        return tr(defaultLocale, text, o1, o2, o3);
    }
    public String tr(String text, Object o1, Object o2, Object o3, Object o4) {
        return tr(defaultLocale, text, o1, o2, o3, o4);
    }
    public String tr(String text, Object[] objects) {
        return tr(defaultLocale, text, objects);
    }
    /* trn(Locale..) and trn(Locale..Object) functions */
    public String trn(Locale locale, String text, String pluralText, long n) {
        if ( ! loadLocale( locale ) )
            return text;
        return resources.get( locale ).trn( text, pluralText, n );
    }
    public String trn(Locale locale, String text, String pluralText, long n, Object o) {
        if ( ! loadLocale( locale ) )
            return text;
        return resources.get( locale ).trn( text, pluralText, n, o );
    }
    public String trn(Locale locale, String text, String pluralText, long n, Object o1, Object o2) {
        if ( ! loadLocale( locale ) )
            return text;
        return resources.get( locale ).trn( text, pluralText, n, o1, o2 );
    }
    public String trn(Locale locale, String text, String pluralText, long n, Object o1, Object o2, Object o3) {
        if ( ! loadLocale( locale ) )
            return text;
        return resources.get( locale ).trn( text, pluralText, n, o1, o2, o3 );
    }
    public String trn(Locale locale, String text, String pluralText, long n, Object o1, Object o2, Object o3, Object o4) {
        if ( ! loadLocale( locale ) )
            return text;
        return resources.get( locale ).trn( text, pluralText, n, o1, o2, o3, o4 );
    }
    public String trn(Locale locale, String text, String pluralText, long n, Object[] objects) {
        if ( ! loadLocale( locale ) )
            return text;
        return resources.get( locale ).trn( text, pluralText, n, objects );
    }
    /* trn(..) and trn(..Object) functions */
    public String trn(String text, String pluralText, long n) {
        return trn(defaultLocale, text, pluralText, n);
    }
    public String trn(String text, String pluralText, long n, Object o) {
        return trn(defaultLocale, text, pluralText, n, o);
    }
    public String trn(String text, String pluralText, long n, Object o1, Object o2) {
        return trn(defaultLocale, text, pluralText, n, o1, o2);
    }
    public String trn(String text, String pluralText, long n, Object o1, Object o2, Object o3) {
        return trn(defaultLocale, text, pluralText, n, o1, o2, o3);
    }
    public String trn(String text, String pluralText, long n, Object o1, Object o2, Object o3, Object o4) {
        return trn(defaultLocale, text, pluralText, n, o1, o2, o3, o4);
    }
    public String trn(String text, String pluralText, long n, Object[] objects) {
        return trn(defaultLocale, text, pluralText, n, objects);
    }
}

