from haloerp.tests.utils import ERPNextTestSuite
from haloerp.utilities.activation import get_level


class TestActivation(ERPNextTestSuite):
	def test_activation(self):
		site_info = {"activation": {"activation_level": 0, "sales_data": []}}
		levels = get_level(site_info)
		self.assertTrue(levels)
