scheduler.__recurring_template='
<div class="dhx_form_repeat"> 
  <form> 
    <div class="dhx_repeat_left"> 
      <label>
        <input class="dhx_repeat_radio" type="radio" name="repeat" value="day" />Denně
      </label><br /> 
      <label>
        <input class="dhx_repeat_radio" type="radio" name="repeat" value="week"/>Týdně
      </label><br /> 
      <label>
        <input class="dhx_repeat_radio" type="radio" name="repeat" value="month" checked />Měsíčně
      </label><br /> 
      <label>
        <input class="dhx_repeat_radio" type="radio" name="repeat" value="year" />Ročně
      </label> 
    </div> 
    <div class="dhx_repeat_divider">
    </div> 
    <div class="dhx_repeat_center"> 
      <div style="display:none;" id="dhx_repeat_day"> 
        <label>Opakované:
          <br/>
        </label> 
        <label>
          <input class="dhx_repeat_radio" type="radio" name="day_type" value="d"/>každý
        </label>
        <input class="dhx_repeat_text" type="text" name="day_count" value="1" />Den<br /> 
        <label>
          <input class="dhx_repeat_radio" type="radio" name="day_type" checked value="w"/>pracovní dny
        </label> 
      </div> 
      <div style="display:none;" id="dhx_repeat_week"> Opakuje každých
        <input class="dhx_repeat_text" type="text" name="week_count" value="1" />Týdnů na:<br /> 
        <table class="dhx_repeat_days"> 
          <tr> <td> 
              <label>
                <input class="dhx_repeat_checkbox" type="checkbox" name="week_day" value="1" />Pondělí
              </label><br /> 
              <label>
                <input class="dhx_repeat_checkbox" type="checkbox" name="week_day" value="4" />Čtvrtek
              </label> </td> <td> 
              <label>
                <input class="dhx_repeat_checkbox" type="checkbox" name="week_day" value="2" />Úterý
              </label><br /> 
              <label>
                <input class="dhx_repeat_checkbox" type="checkbox" name="week_day" value="5" />Pátek
              </label> </td> <td> 
              <label>
                <input class="dhx_repeat_checkbox" type="checkbox" name="week_day" value="3" />Středa
              </label><br /> 
              <label>
                <input class="dhx_repeat_checkbox" type="checkbox" name="week_day" value="6" />Sobota
              </label> </td> <td> 
              <label>
                <input class="dhx_repeat_checkbox" type="checkbox" name="week_day" value="0" />Neděle
              </label><br /><br /> </td> 
          </tr> 
        </table> 
      </div> 
      <div id="dhx_repeat_month"> 
        <label>Opakované:
          <br/>
        </label> 
        <label>
          <input class="dhx_repeat_radio" type="radio" name="month_type" value="d"/>u každého
        </label>
        <input class="dhx_repeat_text" type="text" name="month_day" value="1" />Den každého
        <input class="dhx_repeat_text" type="text" name="month_count" value="1" />Měsíc<br /> 
        <label>
          <input class="dhx_repeat_radio" type="radio" name="month_type" checked value="w"/>na
        </label>
        <input class="dhx_repeat_text" type="text" name="month_week2" value="1" />
        <select name="month_day2">
          <option value="1" selected >Pondělí
          <option value="2">Úterý
          <option value="3">Středa
          <option value="4">Čtvrtek
          <option value="5">Pátek
          <option value="6">Sobota
          <option value="0">Neděle
        </select>každý
        <input class="dhx_repeat_text" type="text" name="month_count2" value="1" />Měsíc<br /> 
      </div> 
      <div style="display:none;" id="dhx_repeat_year"> 
        <label>Opakované:
        </label> 
        <label>
          <input class="dhx_repeat_radio" type="radio" name="year_type" value="d"/>u každého
        </label>
        <input class="dhx_repeat_text" type="text" name="year_day" value="1" />Den v
        <select name="year_month">
          <option value="0" selected >Leden
          <option value="1">Únor
          <option value="2">Březen
          <option value="3">Duben
          <option value="4">Květen
          <option value="5">Červen
          <option value="6">Červenec
          <option value="7">Srpen
          <option value="8">Září
          <option value="9">Říjen
          <option value="10">Listopad
          <option value="11">Prosinec
        </select><br /> 
        <label>
          <input class="dhx_repeat_radio" type="radio" name="year_type" checked value="w"/>na
        </label>
        <input class="dhx_repeat_text" type="text" name="year_week2" value="1" />
        <select name="year_day2">
          <option value="1" selected >Pondělí
          <option value="2">Úterý
          <option value="3">Středa
          <option value="4">Čtvrtek
          <option value="5">Pátek
          <option value="6">Sobota
          <option value="0">Neděle
        </select>v
        <select name="year_month2">
          <option value="0" selected >Leden
          <option value="1">Únor
          <option value="2">Březen
          <option value="3">Duben
          <option value="4">Květen
          <option value="5">Červen
          <option value="6">Červenec
          <option value="7">Srpen
          <option value="8">Září
          <option value="9">Říjen
          <option value="10">Listopad
          <option value="11">Prosinec
        </select><br /> 
      </div> 
    </div> 
    <div class="dhx_repeat_divider">
    </div> 
    <div class="dhx_repeat_right"> 
      <label>
        <input class="dhx_repeat_radio" type="radio" name="end" checked/>bez data ukončení
      </label><br /> 
      <label>
        <input class="dhx_repeat_radio" type="radio" name="end" />po
      </label>
      <input class="dhx_repeat_text" type="text" name="occurences_count" value="1" />Události<br /> 
      <label>
        <input class="dhx_repeat_radio" type="radio" name="end" />Konec
      </label>
      <input class="dhx_repeat_date" type="text" name="date_of_end" value="01.01.2010" /><br /> 
    </div> 
  </form> 
</div> 
<div style="clear:both"> 
</div>';
