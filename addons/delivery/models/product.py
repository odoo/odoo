#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    weight = fields.Float(string='Weight', help="The weight of the contents, not including any packaging, etc.")

