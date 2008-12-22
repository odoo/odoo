##############################################################################
#
# Copyright (c) 2004-2008 Tiny SPRL (http://tiny.be) All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
###############################################################################
!ifndef VERSION
    !error "Do not forget to specify the version of OpenERP - /DVERSION=<VERSION>"
!endif 

!include "MUI.nsh"

;--------------------------------
;General

;Name and file
Name "OpenERP Server"
OutFile "openerp-server-setup-${VERSION}.exe"
SetCompressor lzma
SetCompress auto

;Default installation folder
InstallDir "$PROGRAMFILES\OpenERP Server"

;Get installation folder from registry if available
InstallDirRegKey HKLM "Software\OpenERP Server" ""

BrandingText "OpenERP Server ${VERSION}"

;Vista redirects $SMPROGRAMS to all users without this
RequestExecutionLevel admin

;--------------------------------
;Variables

Var MUI_TEMP
Var STARTMENU_FOLDER

;--------------------------------
;Interface Settings

!define MUI_ABORTWARNING

!define REGKEY "SOFTWARE\$(^Name)"
!define MUI_LANGDLL_REGISTRY_ROOT HKLM
!define MUI_LANGDLL_REGISTRY_KEY ${REGKEY}
!define MUI_LANGDLL_REGISTRY_VALUENAME InstallerLanguage

!insertmacro MUI_RESERVEFILE_LANGDLL
;--------------------------------
;Pages

!define MUI_ICON ".\pixmaps\openerp-icon.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP ".\pixmaps\openerp-intro.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP ".\pixmaps\openerp-intro.bmp"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP_NOSTRETCH
!define MUI_HEADER_TRANSPARENT_TEXT ""
!define MUI_HEADERIMAGE_BITMAP ".\pixmaps\openerp-slogan.bmp"
!define MUI_LICENSEPAGE_TEXT_BOTTOM "$(LicenseText)"
!define MUI_LICENSEPAGE_BUTTON "$(LicenseNext)"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "doc\License.rtf"
!insertmacro MUI_PAGE_DIRECTORY

;Start Menu Folder Page Configuration
!define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKLM" 
!define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\OpenERP Server"
!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "OpenERP Server"

!insertmacro MUI_PAGE_STARTMENU Application $STARTMENU_FOLDER

!insertmacro MUI_PAGE_INSTFILES

!define MUI_FINISHPAGE_NOAUTOCLOSE
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_CHECKED
!define MUI_FINISHPAGE_RUN_TEXT "$(FinishPageText)" 
!define MUI_FINISHPAGE_RUN_FUNCTION "LaunchLink"
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED
!define MUI_FINISHPAGE_SHOWREADME $INSTDIR\README.txt
!insertmacro MUI_PAGE_FINISH


!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
;Languages

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "French"

!macro CreateInternetShortcut FILENAME URL
	WriteINIStr "${FILENAME}.url" "InternetShortcut" "URL" "${URL}"
!macroend

;--------------------------------
;Installer Sections
Function .onInit 
    ;Language selection dialog
    Push ""
    Push ${LANG_ENGLISH}
    Push English
    Push ${LANG_FRENCH}
    Push French
    Push A ; A means auto count languages
    ; for the auto count to work the first empty push (Push "") must remain
    LangDLL::LangDialog "Installer Language" "Please select the language of the installer"

    Pop $LANGUAGE
    StrCmp $LANGUAGE "cancel" 0 +2
        Abort

    ClearErrors
    ReadRegStr $0 HKLM "Software\OpenERP Server" ""
    IfErrors DoInstall 0
        MessageBox MB_OK "$(CannotInstallServerText)"
        Quit
    DoInstall:
FunctionEnd

Section "OpenERP Server" SecOpenERPServer
    nsExec::Exec "net stop openerp-service"
    sleep 2

    SetOutPath "$INSTDIR"

    ;ADD YOUR OWN FILES HERE...
    File /r "dist\*"

    SetOutPath "$INSTDIR\service"
    File /r "win32\dist\*"
    File "win32\start.bat"
    File "win32\stop.bat"

    ;Store installation folder
    WriteRegStr HKLM "Software\OpenERP Server" "" $INSTDIR

!ifndef ALLINONE
    ;Create uninstaller
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OpenERP Server" "DisplayName" "OpenERP Server ${VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OpenERP Server" "UninstallString" "$INSTDIR\Uninstall.exe"
!else
    WriteRegStr HKLM  "Software\OpenERP AllInOne" "UninstallServer" "$INSTDIR\Uninstall.exe"
!endif
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
        ;Create shortcuts
        CreateDirectory "$SMPROGRAMS\$STARTMENU_FOLDER"
        CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\OpenERP Server.lnk" "$INSTDIR\openerp-server.exe"
        CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\Start service.lnk" "$INSTDIR\service\start.bat"
        CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\Stop service.lnk" "$INSTDIR\service\stop.bat"
        CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\Edit config.lnk" "notepad.exe" "$INSTDIR\openerp-server.conf"
        CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\View log.lnk" "notepad.exe" "$INSTDIR\openerp-server.log"
!ifndef ALLINONE
        CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\Uninstall.lnk" "$INSTDIR\uninstall.exe"
!endif
	!insertmacro CreateInternetShortcut "$SMPROGRAMS\$STARTMENU_FOLDER\Forum" "http://www.openerp.com/forum"
	!insertmacro CreateInternetShortcut "$SMPROGRAMS\$STARTMENU_FOLDER\Translation" "https://translations.launchpad.net/openobject"
    !insertmacro MUI_STARTMENU_WRITE_END

    nsExec::Exec '"$INSTDIR\openerp-server.exe" --stop-after-init --logfile "$INSTDIR\openerp-server.log" -s'
    nsExec::Exec '"$INSTDIR\service\OpenERPServerService.exe" -auto -install'

SectionEnd

;Descriptions

 
;--------------------------------
;Uninstaller Section

Section "Uninstall"
    nsExec::Exec "net stop openerp-service"
    sleep 2
    nsExec::Exec '"$INSTDIR\service\OpenERPServerService.exe" -remove'
    sleep 2

    RMDIR /r "$INSTDIR" 
    !insertmacro MUI_STARTMENU_GETFOLDER Application $MUI_TEMP

    Delete "$SMPROGRAMS\$MUI_TEMP\Forum.url"
    Delete "$SMPROGRAMS\$MUI_TEMP\Translation.url"
!ifndef ALLINONE
    Delete "$SMPROGRAMS\$MUI_TEMP\Uninstall.lnk"
!endif 
    Delete "$SMPROGRAMS\$MUI_TEMP\OpenERP Server.lnk"
    Delete "$SMPROGRAMS\$MUI_TEMP\Uninstall.lnk"
    Delete "$SMPROGRAMS\$MUI_TEMP\Start service.lnk"
    Delete "$SMPROGRAMS\$MUI_TEMP\Stop service.lnk"
    Delete "$SMPROGRAMS\$MUI_TEMP\Edit config.lnk"
    Delete "$SMPROGRAMS\$MUI_TEMP\View log.lnk"

    ;Delete empty start menu parent diretories
    StrCpy $MUI_TEMP "$SMPROGRAMS\$MUI_TEMP"
 
    startMenuDeleteLoop:
        ClearErrors
        RMDir $MUI_TEMP
        GetFullPathName $MUI_TEMP "$MUI_TEMP\.."

        IfErrors startMenuDeleteLoopDone

        StrCmp $MUI_TEMP $SMPROGRAMS startMenuDeleteLoopDone startMenuDeleteLoop

    startMenuDeleteLoopDone:

!ifndef ALLINONE
        DeleteRegKey HKEY_LOCAL_MACHINE "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\OpenERP Server"
!else 
        DeleteRegKey HKLM "Software\OpenERP AllInOne\UninstallServer"
!endif
        DeleteRegKey /ifempty HKLM "Software\OpenERP Server"

SectionEnd

Function LaunchLink
    nsExec::Exec "net start openerp-service"
FunctionEnd

LangString LicenseText ${LANG_ENGLISH} "Usually, a proprietary license is provided with the software: limited number of users, limited in time usage, etc. This Open Source license is the opposite: it garantees you the right to use, copy, study, distribute and modify Open ERP for free."
LangString LicenseText ${LANG_FRENCH} "Normalement, une licence propriétaire est fournie avec le logiciel: limitation du nombre d'utilisateurs, limitation dans le temps, etc. Cette licence Open Source est l'opposé: Elle vous garantie le droit d'utiliser, de copier, d'étudier, de distribuer et de modifier Open ERP librement."

LangString LicenseNext ${LANG_ENGLISH} "Next >"
LangString LicenseNext ${LANG_FRENCH} "Suivant >"

LangString FinishPageText ${LANG_ENGLISH} "Start OpenERP Server"
LangString FinishPageText ${LANG_FRENCH} "Lancer le serveur OpenERP"

;Language strings
LangString DESC_SecOpenERPServer ${LANG_ENGLISH} "OpenERP Server."
LangString DESC_SecOpenERPServer ${LANG_FRENCH} "Serveur OpenERP."

LangString CannotInstallServerText ${LANG_ENGLISH} "Can not install the Open ERP Server because a previous installation already exists on this system. Please uninstall your current installation and relaunch this setup wizard."
LangString CannotInstallServerText ${LANG_FRENCH} "Ne peut pas installer le serveur Open ERP parce qu'une installation existe déjà  sur ce système. S'il vous plait, désinstallez votre installation actuelle et relancer l'installeur."


;Assign language strings to sections
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecOpenERPServer} $(DESC_SecOpenERPServer)
!insertmacro MUI_FUNCTION_DESCRIPTION_END
