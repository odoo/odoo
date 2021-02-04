(function () {

  const {whenReady} = owl.utils;

  async function setup() {

    odoo.define('website.website_survey', async function (require) {

      const {Component, Store, mount, QWeb} = owl;
      const {xml} = owl.tags;
      const {useDispatch, useStore, useGetters} = owl.hooks;
      const {Router, RouteComponent} = owl.router;

      var rpc = require('web.rpc');
      var utils = require('web.utils');
      const weUtils = require('web_editor.utils');
      const maxPalette = 16;
      const templates = await owl.utils.loadFile("/website/static/src/xml/theme_preview.xml");
      const qweb = new QWeb({templates});

      const hex2lab = (hex) => {
        let r = parseInt(hex.substring(1, 3), 16) / 255, g = parseInt(hex.substring(3, 5), 16) / 255, b = parseInt(hex.substring(5, 7), 16) / 255, x, y, z;
        r = (r > 0.04045) ? Math.pow((r + 0.055) / 1.055, 2.4) : r / 12.92;
        g = (g > 0.04045) ? Math.pow((g + 0.055) / 1.055, 2.4) : g / 12.92;
        b = (b > 0.04045) ? Math.pow((b + 0.055) / 1.055, 2.4) : b / 12.92;
        x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047;
        y = (r * 0.2126 + g * 0.7152 + b * 0.0722) / 1.00000;
        z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883;
        x = (x > 0.008856) ? Math.pow(x, 1 / 3) : (7.787 * x) + 16 / 116;
        y = (y > 0.008856) ? Math.pow(y, 1 / 3) : (7.787 * y) + 16 / 116;
        z = (z > 0.008856) ? Math.pow(z, 1 / 3) : (7.787 * z) + 16 / 116;
        return [(116 * y) - 16, 500 * (x - y), 200 * (y - z)];
      };

      const deltaE = (hexA, hexB) => {
        let labA = hex2lab(hexA);
        let labB = hex2lab(hexB);
        let deltaL = labA[0] - labB[0];
        let deltaA = labA[1] - labB[1];
        let deltaB = labA[2] - labB[2];
        let c1 = Math.sqrt(labA[1] * labA[1] + labA[2] * labA[2]);
        let c2 = Math.sqrt(labB[1] * labB[1] + labB[2] * labB[2]);
        let deltaC = c1 - c2;
        let deltaH = deltaA * deltaA + deltaB * deltaB - deltaC * deltaC;
        deltaH = deltaH < 0 ? 0 : Math.sqrt(deltaH);
        let sc = 1.0 + 0.045 * c1;
        let sh = 1.0 + 0.015 * c1;
        let deltaLKlsl = deltaL / (1.0);
        let deltaCkcsc = deltaC / (sc);
        let deltaHkhsh = deltaH / (sh);
        let i = deltaLKlsl * deltaLKlsl + deltaCkcsc * deltaCkcsc + deltaHkhsh * deltaHkhsh;
        return i < 0 ? 0 : Math.sqrt(i);
      };

      const SkipButtonTemplate = xml`
        <div class="align-self-end">
          <button class="btn btn-secondary" t-on-click="skip()">Skip</button>
        </div>`;

      class SkipButton extends Component {
        static template = SkipButtonTemplate

        skip() {
          rpc.query({
            model: 'website',
            method: 'skip_survey',
            args: [[parseInt(this.env.router.currentParams.wid)]]
          }).then((route) => {
            window.location = route;
          });
        }
      }

      const WelcomeScreenTemplate = xml`
        <div class="o_survey_screen o_welcome_screen">
          <div class="h-25"/>
          <div class= "d-flex o_welcome_screen_message h-50">
              <div class="align-self-center">
                  <h1>Ready to build the perfect website?</h1>
                  <h1>We'll set you up and running in 4 steps</h1>
                  <button class="btn btn-primary mt-3 btn-lg" t-on-click="goToDescription()">Let's do it</button>
              </div>
          </div>
          <div class="d-flex h-25">
            <SkipButton/>
          </div>
        </div>`;

        class WelcomeScreen extends Component {
          static template = WelcomeScreenTemplate
          static components ={SkipButton};
          dispatch = useDispatch();

          goToDescription() {
            this.env.router.navigate({to: 'SURVEY_DESCRIPTION_SCREEN', params: this.env.router.currentParams});
          }
        }

        const DescriptionScreenTemplate = xml`
        <div class="o_survey_screen o_description_sceen">
          <div class="h-25"/>
          <div class="d-flex h-50">
              <div class="align-self-center mx-auto">
                  <h1>
                      <span>I want </span>
                      <div class="dropdown d-inline-block" style="width: 720px;">
                          <div class="d-inline-block" style="width: 720px;" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                            <a>
                              <t t-if="description.selectedType"><t t-esc="getters.getSelectedType(description.selectedType).label" /></t>
                              <i class="fa fa-angle-down" style="float:right;" title="dropdown_angle_down" role="img"/>
                            </a>
                          </div>
                          <div class="dropdown-menu" style="width: 720px;" role="menu">
                            <t t-foreach="getters.getWebsiteTypes()" t-as="type" t-key="type.name">
                                <a t-att-title="type.name"
                                    t-att-data-id="type.id"
                                    t-on-click="selectWebsiteType"
                                    style="width: 720px;"
                                    class="dropdown-item o_change_website_type">
                                    <t t-esc="type.label"/>
                                </a>
                            </t>
                          </div>
                      </div>
                      <span> for my</span>
                  </h1>
                  <h1>
                      <input class="industry_selection" t-on-blur="blurIndustrySelection" t-on-input="inputIndustrySelection" />
                      <span> business, with the</span>
                  </h1>
                  <h1>
                      <span>main objective to </span>
                      <div class="dropdown d-inline-block" style="width: 620px;">
                          <div class="d-inline-block" style="width: 620px;" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                            <a>
                              <t t-if="description.selectedPurpose"><t t-esc="getters.getSelectedPurpose(description.selectedPurpose).label" /></t>
                              <i class="fa fa-angle-down" style="float:right;" title="dropdown_angle_down" role="img"/>
                            </a>
                          </div>
                          <div class="dropdown-menu" style="width: 620px;" role="menu">
                            <t t-foreach="getters.getWebsitePurpose()" t-as="type" t-key="type.name">
                                <a t-att-title="type.name"
                                    t-att-data-id="type.id"
                                    t-on-click="selectWebsitePurpose"
                                    style="width: 620px;"
                                    class="dropdown-item o_change_website_purpose">
                                    <t t-esc="type.label"/>
                                </a>
                            </t>
                          </div>
                      </div>
                  </h1>
              </div>
          </div>
          <div class="d-flex h-25">
            <SkipButton/>
          </div>
        </div>`;

        class DescriptionScreen extends Component {
          static template = DescriptionScreenTemplate;
          static components ={SkipButton};
          description = useStore((state) => state.description);
          logoValidation = useStore((state) => state.logoValidation);
          labelToCode = {}
          getters = useGetters();
          dispatch = useDispatch();

          mounted() {
            this.dispatch('selectIndustry', undefined);
            $('.industry_selection').autocomplete({
              delay: 400,
              minLength: 1,
              source: this.autocompleteSearch.bind(this),
              select: this.selectIndustry.bind(this),
              classes: {
                  'ui-autocomplete': 'custom-ui-autocomplete',
              }
            });
          }

          autocompleteSearch(request, response) {
            const lcTerm = request.term.toLowerCase();
            const limit = 15;
            let matches = this.description.descriptionData.industries.filter((val) => {
              return val.label.startsWith(lcTerm);
            });
            let results = matches.slice(0, limit);
            this.labelToCode = {};
            let labels = results.map((val) => val.label);
            if (labels.length < limit) {
              let relaxedMatches = this.description.descriptionData.industries.filter((val) => {
                return val.label.includes(lcTerm) && !labels.includes(val.label);
              });
              relaxedMatches = relaxedMatches.slice(0, limit - labels.length);
              results = results.concat(relaxedMatches);
              labels = results.map((val) => val.label);
            }
            results.forEach((r) => {
              this.labelToCode[r.label] = r.code;
            });
            response(labels);
          }

          selectIndustry(_, ui) {
            this.dispatch('selectIndustry', this.labelToCode[ui.item.label]);
            this.checkDescriptionCompletion();
          }

          blurIndustrySelection(ev) {
            const label = this.labelToCode[ev.target.value];
            this.dispatch('selectIndustry', label);
            if (label === undefined) {
              $('.industry_selection').val('');
            } else {
              this.checkDescriptionCompletion();
            }
          }

          inputIndustrySelection(ev) {
            this.dispatch('selectIndustry', this.labelToCode[ev.target.value]);
          }

          selectWebsiteType(ev) {
            const id = $(ev.target).data('id');
            this.dispatch('selectWebsiteType', id);
            this.checkDescriptionCompletion();
          }

          selectWebsitePurpose(ev) {
            const id = $(ev.target).data('id');
            this.dispatch('selectWebsitePurpose', id);
            this.checkDescriptionCompletion();
          }

          checkDescriptionCompletion() {
            if (this.description.selectedType && this.description.selectedPurpose && this.description.selectedIndustry) {
              if (this.logoValidation.logo !== false) {
                this.env.router.navigate({to: 'SURVEY_LOGO_VALIDATION_SCREEN', params: this.env.router.currentParams});
              } else {
                this.env.router.navigate({to: 'SURVEY_PALETTE_SELECTION_SCREEN', params: this.env.router.currentParams});
              }
            }
          }
        }

        const LogoValidationScreenTemplate = xml`
        <div class="o_survey_screen o_logo_validation_screen">
          <div class="h-25"/>
          <div class="d-flex h-50">
              <div class="align-self-center mx-auto">
                  <h1 class="text-center">Is this your logo?</h1>
                  <div class="align-self-center mx-auto mt-4 mb-4" style="width: fit-content;">
                      <img class="website_logo" t-attf-src="{{logoValidation.logo}}"/>
                  </div>
                  <div class="align-self-center mx-auto" style="width:fit-content;">
                      <button class="btn btn-lg btn-success mr-2" t-on-click="validateLogo(true)">Yes</button>
                      <button class="btn btn-lg btn-danger ml-2" t-on-click="validateLogo(false)">No</button>
                  </div>
              </div>
          </div>
          <div class="d-flex h-25">
            <SkipButton/>
          </div>
        </div>
        `;

        class LogoValidationScreen extends Component {
          static template = LogoValidationScreenTemplate;
          static components ={SkipButton};
          logoValidation = useStore((state) => state.logoValidation);
          dispatch = useDispatch();

          mounted() {
            if (this.logoValidation.logo === false) {
              this.env.router.navigate({to: 'SURVEY_PALETTE_SELECTION_SCREEN', params: this.env.router.currentParams});
            }
          }

          async validateLogo(isValid) {
            this.dispatch('validateLogo', isValid);
            let color1 = false;
            let color2 = false;
            if (isValid) {
              let img = this.logoValidation.logo.split(',', 2)[1];
              const colors = await rpc.query({
                model: 'base.document.layout',
                method: 'extract_image_primary_secondary_colors',
                args: [img]
              });
              color1 = colors[0];
              color2 = colors[1];
            }
            this.dispatch('setRecommendedPalette', color1, color2);
            this.env.router.navigate({to: 'SURVEY_PALETTE_SELECTION_SCREEN', params: this.env.router.currentParams});
          }
        }

        const PaletteSelectionScreenTemplate = xml`
        <div class="o_survey_screen o_palette_selection_screen">
          <div class="d-flex" style="min-height: 20%;">
              <div class="align-self-center mx-auto">
                  <input type="file" class="logo_selection_input" t-on-change="changeLogo" style="display:none" name="logo_selection" accept="image/*"/>
                  <h1 class="text-center">Choose Your Brand Color <span class="text-muted">or </span><span t-on-click="uploadLogo" class="text-primary" style="cursor: pointer;">Upload</span> your logo</h1>
              </div>
          </div>
          <div class="d-flex">
            <div class="w-100 palette_selection container">
              <t t-foreach="getters.getPalettes()" t-as="row" t-key="row_index">
                <div class="row palette_row align-items-end">
                  <t t-foreach="row" t-as="palette" t-key="palette_index">
                    <t t-if="palette.type == 'empty'">
                      <div class="col-md"/>
                    </t>
                    <t t-else="">
                      <div class="col-md">
                        <t t-if="palette.type == 'recommended'">
                          <h2 class="text-center text-muted">recommended</h2>
                        </t>
                        <div class="palette_card" t-on-click="selectPalette(palette.id)">
                          <div class="row">
                            <div class="color_sample first" t-attf-style="background-color: {{palette.color1}}"/>
                            <div class="color_sample second" t-attf-style="background-color: {{palette.color2}}"/>
                            <div class="color_sample third" t-attf-style="background-color: {{palette.color3}}"/>
                          </div>
                        </div>
                      </div>
                    </t>
                  </t>
                </div>
              </t>
            </div>
          </div>
          <div>
            <div style="position: absolute; bottom: 20px;">
              <SkipButton/>
            </div>
          </div>
        </div>
        `;

        class PaletteSelectionScreen extends Component {
          static template = PaletteSelectionScreenTemplate;
          static components ={SkipButton};
          getters = useGetters();
          dispatch = useDispatch();

          uploadLogo() {
            $('.logo_selection_input').click();
          }

          changeLogo() {
            const logoSelectInput = $('.logo_selection_input');
            const self = this;
            if (logoSelectInput[0].files.length === 1) {
                const file = logoSelectInput[0].files[0];
                utils.getDataURLFromFile(file).then(function (data) {
                    self.dispatch('changeLogo', data);
                    self.env.router.navigate({to: 'SURVEY_LOGO_VALIDATION_SCREEN', params: self.env.router.currentParams});
                });
            }
          }

          selectPalette(paletteId) {
            this.dispatch('selectPalette', paletteId);
            this.env.router.navigate({to: 'SURVEY_FEATURES_SELECTION_SCREEN', params: this.env.router.currentParams});
          }
        }

        const FeatureSelectionScreenTemplate = xml`
        <div class="o_survey_screen o_feature_selection_screen">
          <div class="d-flex" style="min-height: 20%;">
              <div class="align-self-center mx-auto w-75">
                  <h1 class="text-left">Add pages or features</h1>
              </div>
          </div>
          <div class="w-75 mx-auto" style="height: 75%;">
              <div class="w-100 page_feature_selection container">
                <t t-foreach="getters.getFeatures()" t-as="row" t-key="row_index">
                  <div class="row">
                    <t t-foreach="row" t-as="feature" t-key="feature_index">
                      <t t-if="feature.type == 'empty'">
                        <div class="col-sm"/>
                      </t>
                      <t t-else="">
                        <div class="col-sm">
                          <div t-attf-class="page_feature_card {{feature.selected ? 'selected' : ''}}" t-on-click="dispatch('toggleFeature', feature.id)">
                            <h2><t t-esc="feature.title"/> <i class="fa fa-check-circle fa-lg"></i></h2>
                            <p><t t-esc="feature.description"/></p>
                          </div>
                        </div>
                      </t>
                    </t>
                  </div>
                </t>
              </div>
              <div class="d-flex align-self-end w-100 justify-content-end" style="min-height: 50px;">
                  <button class="btn btn-primary btn-lg mt-3 mb-3" t-on-click="buildWebsite()">Build my website</button>
              </div>
          </div>
          <div>
            <div style="position: absolute; bottom: 20px;">
              <SkipButton/>
            </div>
          </div>
        </div>
        `;

        class FeaturesSelectionScreen extends Component {
          static template = FeatureSelectionScreenTemplate;
          static components ={SkipButton};
          featureSelection = useStore((state) => state.featureSelection);
          description = useStore((state) => state.description);
          getters = useGetters();
          dispatch = useDispatch();

          async buildWebsite() {
            const industryCode = this.description.selectedIndustry;
            if (!industryCode) {
              this.env.router.navigate({to: 'SURVEY_DESCRIPTION_SCREEN', params: this.env.router.currentParams});
              return;
            }
            const params = {
              description: {
                industryCode: industryCode
              }
            };
            const res = await rpc.query({
              model: 'website',
              method: 'get_recommended_themes',
              args: [[parseInt(this.env.router.currentParams.wid)], params],
            });

            if (res.themes.length !== 3) {
              rpc.query({
                model: 'website',
                method: 'skip_survey',
                args: [[parseInt(this.env.router.currentParams.wid)]]
              }).then((route) => {
                window.location = route;
              });
            }

            this.dispatch('updateRecommendedThemes', res.themes);
            this.env.router.navigate({to: 'SURVEY_THEME_SELECTION_SCREEN', params: this.env.router.currentParams});
          }
        }

        const ThemeSelectionScreenTemplate = xml`
        <div class="o_survey_screen o_theme_selection_screen">
          <div class="d-flex h-25">
              <div class="align-self-center mx-auto">
                  <h1 class="text-center">Choose your favorite style</h1>
              </div>
          </div>
          <div class="d-flex flex-row justify-content-center align-items-end h-75">
              <div class="theme_preview small">
                  <div class="theme_screenshot theme_recommendation_2" t-attf-style="background-image: url('{{themeSelection.secondTheme.url}}');">
                      <div class="button_area">
                          <button class="btn btn-primary" t-on-click="chooseTheme(themeSelection.secondTheme.id)">Use this theme</button>
                      </div>
                  </div>
              </div>
              <div style="width: 3%;"/>
              <div class="theme_preview large">
                  <div class="theme_screenshot theme_recommendation_1" t-attf-style="background-image: url('{{themeSelection.firstTheme.url}}');">
                      <div class="button_area">
                          <button class="btn btn-primary" t-on-click="chooseTheme(themeSelection.firstTheme.id)">Use this theme</button>
                      </div>
                  </div>
              </div>
              <div style="width: 3%;"/>
              <div class="theme_preview small">
                  <div class="theme_screenshot theme_recommendation_3" t-attf-style="background-image: url('{{themeSelection.thirdTheme.url}}');">
                      <div class="button_area">
                          <button class="btn btn-primary" t-on-click="chooseTheme(themeSelection.thirdTheme.id)">Use this theme</button>
                      </div>
                  </div>
              </div>
          </div>
        </div>
        `;

        class ThemeSelectionScreen extends Component {
          static template = ThemeSelectionScreenTemplate;
          logoValidation = useStore((state) => state.logoValidation);
          themeSelection = useStore((state) => state.themeSelection);
          featureSelection = useStore((state) => state.featureSelection);
          description = useStore((state) => state.description);
          palette = useStore((state) => state.paletteSelection);
          loader = $(qweb.renderToString('website.ThemePreview.Loader'))[0];

          chooseTheme(themeId) {
            if (themeId !== undefined) {
              this.addLoader();
              const selectedFeatures = Object.values(this.featureSelection.features).filter((feature) => feature.selected).map((feature) => feature.id);
              const logo = this.logoValidation.isLogoValid ? this.logoValidation.logo : false;
              const data = {
                selected_feautures: selectedFeatures,
                logo: logo,
                industry: this.description.selectedIndustry,
                selected_palette: this.palette.selectedPalette.id,
              };
              rpc.query({
                model: 'ir.module.module',
                method: 'button_choose_theme',
                args: [[themeId], data],
              }).then((resp) => {
                window.location = resp.url;
              });
            }
          }

          addLoader() {
            $('body').append(this.loader);
          }

        }

        const AppTemplate = xml/* xml */`
          <div class="o_survey_container">
            <RouteComponent />
          </div>
        `;

        class App extends Component {
          static template = AppTemplate;
          static components ={RouteComponent};
        }

        const ROUTES = [
          {name: "SURVEY_WELCOME_SCREEN", path: "/website/survey/1/{{wid}}", component: WelcomeScreen},
          {name: "SURVEY_DESCRIPTION_SCREEN", path: "/website/survey/2/{{wid}}", component: DescriptionScreen},
          {name: "SURVEY_LOGO_VALIDATION_SCREEN", path: "/website/survey/3/{{wid}}", component: LogoValidationScreen},
          {name: "SURVEY_PALETTE_SELECTION_SCREEN", path: "/website/survey/4/{{wid}}", component: PaletteSelectionScreen},
          {name: "SURVEY_FEATURES_SELECTION_SCREEN", path: "/website/survey/5/{{wid}}", component: FeaturesSelectionScreen},
          {name: "SURVEY_THEME_SELECTION_SCREEN", path: "/website/survey/6/{{wid}}", component: ThemeSelectionScreen},
        ];

        const actions = {
          selectWebsiteType({state}, id) {
            Object.values(state.featureSelection.features).forEach((feature) => {
              if (feature.websiteType === state.description.descriptionData.websiteTypes[id].name) {
                feature.selected = true;
              } else {
                feature.selected = false;
              }
            });
            state.description.selectedType = id;
          },
          selectWebsitePurpose({state}, id) {
            state.description.selectedPurpose = id;
          },
          selectIndustry({state}, code) {
            state.description.selectedIndustry = code;
          },
          validateLogo({state}, isValid) {
            state.logoValidation.isLogoValid = isValid;
          },
          changeLogo({state}, data) {
            state.logoValidation.logo = data;
          },
          selectPalette({state}, paletteId) {
            state.paletteSelection.selectedPalette = state.paletteSelection.palettes[paletteId];
          },
          toggleFeature({state}, featureId) {
            const isSelected = state.featureSelection.features[featureId].selected;
            state.featureSelection.features[featureId].selected = !isSelected;
          },
          setRecommendedPalette({state}, color1, color2) {
            let palettes = [];
            if (color1 && color2) {
              for (let paletteName in state.paletteSelection.allPalettes) {
                const paletteColor1 = state.paletteSelection.allPalettes[paletteName]['color1'];
                const paletteColor2 = state.paletteSelection.allPalettes[paletteName]['color2'];
                const delta1 = deltaE(color1, paletteColor1);
                const delta2 = deltaE(color2, paletteColor2);
                state.paletteSelection.allPalettes[paletteName]['score'] = (delta1 + delta2) / 2;
              }
              palettes = Object.values(state.paletteSelection.allPalettes).sort((a, b) => a['score'] - b['score']);
              palettes[0].type = 'recommended';
            } else {
              palettes = Object.values(state.paletteSelection.allPalettes);
            }
            const selectedPalettes = {};
            for (let i = 0; i < maxPalette; i += 1) {
              selectedPalettes[palettes[i].id] = palettes[i];
              if (i > 0) {
                palettes[i].type = 'base';
              }
            }
            if (selectedPalettes) {
              state.paletteSelection.palettes = selectedPalettes;
            }
          },
          updateRecommendedThemes({state}, themes) {
            if (themes[0]) {
              state.themeSelection.firstTheme.name = themes[0].name;
              state.themeSelection.firstTheme.url = themes[0].url;
              state.themeSelection.firstTheme.id = themes[0].id;
            }
            if (themes[1]) {
              state.themeSelection.secondTheme.name = themes[1].name;
              state.themeSelection.secondTheme.url = themes[1].url;
              state.themeSelection.secondTheme.id = themes[1].id;
            }
            if (themes[2]) {
              state.themeSelection.thirdTheme.name = themes[2].name;
              state.themeSelection.thirdTheme.url = themes[2].url;
              state.themeSelection.thirdTheme.id = themes[2].id;
            }
          }
        };

        const getters = {
          getWebsiteTypes({state}) {
            return Object.values(state.description.descriptionData.websiteTypes).map(x => x);
          },

          getSelectedType({state}, id) {
            return id ? state.description.descriptionData.websiteTypes[id] : undefined;
          },

          getWebsitePurpose({state}) {
            return Object.values(state.description.descriptionData.websitePurposes).map(x => x);
          },

          getSelectedPurpose({state}, id) {
            return id ? state.description.descriptionData.websitePurposes[id] : undefined;
          },

          getFeatures({state}) {
            const columnNumber = 3;
            const featureRows = [];

            const features = Object.values(state.featureSelection.features);
            let currentRow = [];
            for (let i = 0; i < features.length; i += 1) {
              currentRow.push(features[i]);
              if (currentRow.length === columnNumber) {
                featureRows.push(currentRow);
                currentRow = [];
              }
            }
            if (currentRow.length > 0) {
              const rowLength = currentRow.length;
              for (let i = 0; i < (columnNumber - rowLength); i += 1) {
                currentRow.push({
                  type: 'empty'
                });
              }
              featureRows.push(currentRow);
            }
            return featureRows;
          },

          getPalettes({state}) {
            const columnNumber = 4;
            const paletteRows = [];
            let palettes = Object.values(state.paletteSelection.palettes);
            let currentRow = [];
            for (let i = 0; i < palettes.length; i += 1) {
              currentRow.push(palettes[i]);
              if (currentRow.length === columnNumber) {
                paletteRows.push(currentRow);
                currentRow = [];
              }
            }
            if (currentRow.length > 0) {
              const rowLength = currentRow.length;
              for (let i = 0; i < (columnNumber - rowLength); i += 1) {
                currentRow.push({
                  type: 'empty'
                });
              }
              paletteRows.push(currentRow);
            }
            return paletteRows;
          },
        };

        async function getInitialState(wid) {

          const feautureSelection = rpc.query({
            model: 'website.survey.feature',
            method: 'search_read',
            fields: ['title', 'description', 'type', 'website_type'],
          }).then(function (results) {
            const features = {};
            for (let i = 0; i < results.length; i += 1) {
              features[results[i].id] = {
                id: results[i].id,
                title: results[i].title,
                description: results[i].description,
                type: results[i].type,
                websiteType: results[i].website_type,
                selected: false
              };
            }
            return features;
          }).catch(function (_) {
              return {};
          });

          const logoValidation = rpc.query({
            model: 'website',
            method: 'get_survey_logo',
            args: [[parseInt(wid)]],
          });

          const style = window.getComputedStyle(document.documentElement);
          const themeNames = weUtils.getCSSVariableValue('theme-names', style).split(' ');
          const allPalettes = {};
          const palettes = {};
          themeNames.forEach((rawName) => {
            const name = rawName.replace(/'/g, "");
            const count = weUtils.getCSSVariableValue(`o-count-${name}`, style);
            for (let i = 1; i <= count; i += 1) {
              const paletteName = `${name}-${i}`;
              const palette = {};
              palette['id'] = paletteName;
              palette.type = 'base';
              for (let j = 1; j <= 3; j += 1) {
                const color = weUtils.getCSSVariableValue(`o-palette-${name}-${i}-o-color-${j}`, style);
                palette[`color${j}`] = color;
              }
              // Remove duplicated palettes
              let duplicate = false;
              for (const validatedPalette of Object.values(allPalettes)) {
                if (validatedPalette.color1.toLowerCase() === palette.color1.toLowerCase() && validatedPalette.color2.toLowerCase() === palette.color2.toLowerCase()) {
                  duplicate = true;
                }
              }
              if (!duplicate) {
                allPalettes[paletteName] = palette;
                if (Object.keys(palettes).length < maxPalette) {
                  palettes[paletteName] = allPalettes[paletteName];
                }
              }
            }
          });

          return Promise.all([feautureSelection, logoValidation]).then((vals) => {
            return {
              description: {
                selectedType: undefined,
                selectedPurpose: undefined,
                selectedIndustry: undefined,
                descriptionData: descriptionData
              },
              logoValidation: {
                logo: vals[1],
                isLogoValid: false,
              },
              paletteSelection: {
                selectedPalette: undefined,
                recommendedPalette: undefined,
                palettes: palettes,
                allPalettes: allPalettes,
              },
              featureSelection: {
                features: vals[0],
              },
              themeSelection: {
                firstTheme: {
                  name: undefined,
                  url: undefined,
                  id: undefined,
                },
                secondTheme: {
                  name: undefined,
                  url: undefined,
                  id: undefined,
                },
                thirdTheme: {
                  name: undefined,
                  url: undefined,
                  id: undefined,
                }
              }
            };
          });
        }

        async function makeStore(wid) {
          const state = await getInitialState(wid);
          const store = new Store({state, actions, getters});
          return store;
        }

        async function makeEnvironment() {
          const env = {};
          env.router = new Router(env, ROUTES);
          await env.router.start();
          env.store = await makeStore(env.router.currentParams.wid);
          return env;
        }

        const env = await makeEnvironment();
        $('body').removeClass('o_connected_user');
        mount(App, {target: document.body, env});
    });
  }

  whenReady(setup);

})();
