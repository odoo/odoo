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

import net.sf.jasperreports.engine.JRDefaultScriptlet;
import net.sf.jasperreports.engine.design.JRCompilationUnit;
import net.sf.jasperreports.compilers.JRGroovyCompiler;
import net.sf.jasperreports.engine.JRException;
import net.sf.jasperreports.engine.design.JRSourceCompileTask;
import net.sf.jasperreports.engine.design.JRCompilationSourceCode;
import net.sf.jasperreports.engine.JRExpression;
import net.sf.jasperreports.engine.design.JRDefaultCompilationSourceCode;
import net.sf.jasperreports.engine.design.JRDesignExpression;
import net.sf.jasperreports.engine.JRExpressionChunk;
import net.sf.jasperreports.engine.design.JRDesignExpressionChunk;
import net.sf.jasperreports.engine.JRReport;

import java.util.List;

public class I18nGroovyCompiler extends JRGroovyCompiler {
    static public List sourceCodeList = null; 
    static private String newImport = "import com.nantic.jasperreports.Translator;\nimport com.nantic.jasperreports.CsvMultiLanguageDataSource;\nimport net.sf.jasperreports.engine.JRDataSource;";
    static private String newVariable = "public Translator translator = null;\n";
    static private String returnTranslator = 
        "if (translator == null) {\n" + 
        "    // For some reason parameter_REPORT_DATA_SOURCE may become of type\n" +
        "    // net.sf.jasperreports.engine.data.ListOfArrayDataSource\n" +
        "    // even if the value in the parameters map is actually a CsvMultiLanguageDataSource.\n" +
        "    // So we use the map instead of parameter_REPORT_DATA_SOURCE.\n" +
        "    JRDataSource dataSource = (JRDataSource)parameter_REPORT_PARAMETERS_MAP.getValue().get(\"REPORT_DATA_SOURCE\");\n" + 
        "    if (dataSource.class == CsvMultiLanguageDataSource) {\n" + 
        "        translator = ((CsvMultiLanguageDataSource)dataSource).getTranslator();\n" +
        "    } else if (translator == parameter_REPORT_PARAMETERS_MAP.getValue().containsKey(\"TRANSLATOR\")){\n"+
        "        translator = (CsvMultiLanguageDataSource)parameter_TRANSLATOR.getValue();\n" + 
        "    } else {\n" +
        "        translator = new Translator(null, null);\n" +
        "    }\n" +
        "}\n" + 
        "return translator";
    static private String newFunction = 
        "public String tr(Locale locale, String text) {\n" +
            "TRANSLATOR.tr(locale, text);\n" +
        "}\n" +
        "public String tr(Locale locale, String text, Object o) {\n" +
            "TRANSLATOR.tr(locale, text, o);\n" +
        "}\n" +
        "public String tr(Locale locale, String text, Object o1, Object o2) {\n" +
            "TRANSLATOR.tr(locale, text, o1, o2);\n" +
        "}\n" +
        "public String tr(Locale locale, String text, Object o1, Object o2, Object o3) {\n" +
            "TRANSLATOR.tr(locale, text, o1, o2, o3);\n" +
        "}\n" +
        "public String tr(Locale locale, String text, Object o1, Object o2, Object o3, Object o4) {\n" +
            "TRANSLATOR.tr(locale, text, o1, o2, o3, o4);\n" +
        "}\n" +
        "public String tr(Locale locale, String text, Object[] objects) {\n" +
            "TRANSLATOR.tr(locale, text, objects);\n" +
        "}\n" +
        "public String tr(String text) {\n" +
            "TRANSLATOR.tr(text);\n" +
        "}\n" +
        "public String tr(String text, Object o) {\n" +
            "TRANSLATOR.tr(text, o);\n" +
        "}\n" +
        "public String tr(String text, Object o1, Object o2) {\n" +
            "TRANSLATOR.tr(text, o1, o2);\n" +
        "}\n" +
        "public String tr(String text, Object o1, Object o2, Object o3) {\n" +
            "TRANSLATOR.tr(text, o1, o2, o3);\n" +
        "}\n" +
        "public String tr(String text, Object o1, Object o2, Object o3, Object o4) {\n" +
            "TRANSLATOR.tr(text, o1, o2, o3, o4);\n" +
        "}\n" +
        "public String tr(String text, Object[] objects) {\n" +
            "TRANSLATOR.tr(text, objects);\n" +
        "}\n" +
        "public String trn(Locale locale, String text, String pluralText, long n) {\n" +
            "TRANSLATOR.trn(locale, text, pluralText, n);\n" +
        "}\n" +
        "public String trn(Locale locale, String text, String pluralText, long n, Object o) {\n" +
            "TRANSLATOR.trn(locale, text, pluralText, n, o);\n" +
        "}\n" +
        "public String trn(Locale locale, String text, String pluralText, long n, Object o1, Object o2) {\n" +
            "TRANSLATOR.trn(locale, text, pluralText, n, o1, o2);\n" +
        "}\n" +
        "public String trn(Locale locale, String text, String pluralText, long n, Object o1, Object o2, Object o3) {\n" +
            "TRANSLATOR.trn(locale, text, pluralText, n, o1, o2, o3);\n" +
        "}\n" +
        "public String trn(Locale locale, String text, String pluralText, long n, Object o1, Object o2, Object o3, Object o4) {\n" +
            "TRANSLATOR.trn(locale, text, pluralText, n, o1, o2, o3, o4);\n" +
        "}\n" +
        "public String trn(Locale locale, String text, String pluralText, long n, Object[] objects) {\n" +
            "TRANSLATOR.trn(locale, text, pluralText, n, objects);\n" +
        "}\n" +
        "public String trn(String text, String pluralText, long n) {\n" +
            "TRANSLATOR.trn(text, pluralText, n);\n" +
        "}\n" +
        "public String trn(String text, String pluralText, long n, Object o) {\n" +
            "TRANSLATOR.trn(text, pluralText, n, o);\n" +
        "}\n" +
        "public String trn(String text, String pluralText, long n, Object o1, Object o2) {\n" +
            "TRANSLATOR.trn(text, pluralText, n, o1, o2);\n" +
        "}\n" +
        "public String trn(String text, String pluralText, long n, Object o1, Object o2, Object o3) {\n" +
            "TRANSLATOR.trn(text, pluralText, n, o1, o2, o3);\n" +
        "}\n" +
        "public String trn(String text, String pluralText, long n, Object o1, Object o2, Object o3, Object o4) {\n" +
            "TRANSLATOR.trn(text, pluralText, n, o1, o2, o3, o4);\n" +
        "}\n" +
        "public String trn(String text, String pluralText, long n, Object[] objects) {\n" +
            "TRANSLATOR.trn(text, pluralText, n, objects);\n" +
        "}\n" +
        "public String trl(String localeCode, String text) {\n" +
            "TRANSLATOR.trl(localeCode, text);\n" +
        "}\n" +
        "public String trl(String localeCode, String text, Object o) {\n" +
            "TRANSLATOR.trl(localeCode, text, o);\n" +
        "}\n" +
        "public String trl(String localeCode, String text, Object o1, Object o2) {\n" +
            "TRANSLATOR.trl(localeCode, text, o1, o2);\n" +
        "}\n" +
        "public String trl(String localeCode, String text, Object o1, Object o2, Object o3) {\n" +
            "TRANSLATOR.trl(localeCode, text, o1, o2, o3);\n" +
        "}\n" +
        "public String trl(String localeCode, String text, Object o1, Object o2, Object o3, Object o4) {\n" +
            "TRANSLATOR.trl(localeCode, text, o1, o2, o3, o4);\n" +
        "}\n" +
        "public String trl(String localeCode, String text, Object[] objects) {\n" +
            "TRANSLATOR.trl(localeCode, text, objects);\n" +
        "}\n";

    public I18nGroovyCompiler() {
        super();
    }

    protected JRCompilationSourceCode generateSourceCode(JRSourceCompileTask sourceTask) throws JRException {
        JRCompilationSourceCode superCode = super.generateSourceCode(sourceTask);
        String code = superCode.getCode();
        String existingCode;

        existingCode = "import java.net";
        code = code.replace( existingCode, newImport + "\n" + existingCode );

        existingCode = "void customizedInit";
        String newFunctionCode = newFunction.replaceAll("TRANSLATOR", returnTranslator);
        code = code.replace( existingCode, newFunctionCode + "\n\n" + existingCode );

        existingCode = "private JRFillParameter parameter_JASPER_REPORT = null;";
        code = code.replace( existingCode, existingCode + "\n" + newVariable + "\n" );

        JRDesignExpression ee;
        JRExpression[] expressions = new JRExpression[sourceTask.getExpressions().size()];
        int i = -1;
        for (Object o : sourceTask.getExpressions() ) {
            JRExpression e = (JRExpression)o;
            i++;

            ee = new JRDesignExpression();
            ee.setValueClass( e.getValueClass() );
            ee.setValueClassName( e.getValueClassName() );
            ee.setText( e.getText().replaceAll( "_\\(", "a(" ) );
            ee.setId( e.getId() );
            if ( e.getChunks() != null ) {
                for (Object chunk : e.getChunks() ) {
                    JRDesignExpressionChunk newChunk = new JRDesignExpressionChunk();
                    newChunk.setType( ((JRExpressionChunk)chunk).getType() );
                    newChunk.setText( ((JRExpressionChunk)chunk).getText() );
                    ee.addChunk( newChunk );
                }
            }
            expressions[i] = ee;
        }
        JRDefaultCompilationSourceCode newCode = new JRDefaultCompilationSourceCode( code, expressions );
        // Store last generated source code so it can be extracted
        if (sourceCodeList != null)
            sourceCodeList.add( (Object) code );
        return newCode;
    }

    protected void checkLanguage(String language) throws JRException {
        if ( 
            !JRReport.LANGUAGE_GROOVY.equals(language)
            && !JRReport.LANGUAGE_JAVA.equals(language) 
            && !language.equals("i18ngroovy") 
            )
        {
            throw new JRException(
                "Language \"" + language
                + "\" not supported by this report compiler.\n"
                + "Expecting \"i18ngroovy\", \"groovy\" or \"java\" instead."
            );
        }
    }
}
