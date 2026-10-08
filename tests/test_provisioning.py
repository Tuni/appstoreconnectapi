import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'appstoreconnect'))
from api import Api, APIError, BASE_API, HttpMethod
from resources import BundleId, BundleIdCapability


class ProvisioningTests(unittest.TestCase):
    def setUp(self):
        # Skip JWT generation: no key, credentials, or network access.
        self.api = Api.__new__(Api)
        self.api.submit_stats = False
        self.api._debug = False
        self.api._api_call = Mock()
        self.bundle = BundleId({'id': 'BUNDLE', 'attributes': {
            'identifier': 'com.example.extension', 'name': 'Extension',
            'platform': 'UNIVERSAL', 'seedId': 'TEAM',
        }}, self.api)
        self.capability = BundleIdCapability({'id': 'CAPABILITY', 'attributes': {
            'capabilityType': 'APP_GROUPS', 'settings': None,
        }}, self.api)

    def test_register_payload_omits_optional_prefix_and_relationships(self):
        self.api._api_call.return_value = {'data': self.bundle._data}
        result = self.api.register_new_bundle_id('Extension', 'com.example.extension', 'UNIVERSAL')
        self.api._api_call.assert_called_once_with(BASE_API + '/v1/bundleIds', HttpMethod.POST, {
            'data': {'type': 'bundleIds', 'attributes': {
                'name': 'Extension', 'identifier': 'com.example.extension', 'platform': 'UNIVERSAL',
            }, 'relationships': {}},
        })
        self.assertIsInstance(result, BundleId)
        self.assertEqual(result.id, 'BUNDLE')

    def test_register_explicit_seed(self):
        self.api._api_call.return_value = {'data': self.bundle._data}
        self.api.register_new_bundle_id('Extension', 'com.example.extension', 'UNIVERSAL', seedId='TEAM')
        self.assertEqual(self.api._api_call.call_args[0][2]['data']['attributes']['seedId'], 'TEAM')

    def test_read_uses_resource_id(self):
        self.api._api_call.return_value = {'data': self.bundle._data}
        result = self.api.read_bundle_id('BUNDLE')
        self.api._api_call.assert_called_once_with(BASE_API + '/v1/bundleIds/BUNDLE')
        self.assertEqual(result.identifier, 'com.example.extension')

    def test_rename_only_writes_name(self):
        self.api._api_call.return_value = {'data': self.bundle._data}
        self.api.modify_bundle_id(self.bundle, 'Renamed')
        self.api._api_call.assert_called_once_with(BASE_API + '/v1/bundleIds/BUNDLE', HttpMethod.PATCH, {
            'data': {'id': 'BUNDLE', 'type': 'bundleIds', 'attributes': {'name': 'Renamed'}, 'relationships': {}},
        })

    def test_list_capabilities_is_lazy_and_follows_next_page(self):
        next_url = BASE_API + '/v1/bundleIds/BUNDLE/bundleIdCapabilities?cursor=next'
        self.api._api_call.side_effect = [
            {'data': [self.capability._data], 'links': {'next': next_url}, 'meta': {'paging': {'total': 2}}},
            {'data': [{'id': 'SECOND', 'attributes': {'capabilityType': 'NETWORK_EXTENSIONS'}}], 'links': {}},
        ]
        result = self.api.list_bundle_id_capabilities('BUNDLE')
        self.api._api_call.assert_not_called()
        ids = [cap.id for cap in result]
        self.assertEqual(ids, ['CAPABILITY', 'SECOND'])
        self.assertEqual([c.args[0] for c in self.api._api_call.call_args_list], [
            BASE_API + '/v1/bundleIds/BUNDLE/bundleIdCapabilities', next_url,
        ])

    def test_enable_links_exact_bundle_without_group_or_optional_settings(self):
        self.api._api_call.return_value = {'data': self.capability._data}
        result = self.api.enable_bundle_id_capability(self.bundle, 'APP_GROUPS')
        self.api._api_call.assert_called_once_with(BASE_API + '/v1/bundleIdCapabilities', HttpMethod.POST, {
            'data': {'type': 'bundleIdCapabilities', 'attributes': {'capabilityType': 'APP_GROUPS'},
                     'relationships': {'bundleId': {'data': {'id': 'BUNDLE', 'type': 'bundleIds'}}}},
        })
        self.assertIsInstance(result, BundleIdCapability)

    def test_enable_passes_settings_without_modifying_them(self):
        settings = [{'key': 'EXAMPLE', 'options': [{'key': 'OPTION', 'enabled': True}]}]
        self.api._api_call.return_value = {'data': self.capability._data}
        self.api.enable_bundle_id_capability(self.bundle, 'EXAMPLE', settings=settings)
        self.assertEqual(self.api._api_call.call_args[0][2]['data']['attributes']['settings'], settings)

    def test_read_capability(self):
        self.api._api_call.return_value = {'data': self.capability._data}
        result = self.api.read_bundle_id_capability('CAPABILITY')
        self.api._api_call.assert_called_once_with(BASE_API + '/v1/bundleIdCapabilities/CAPABILITY')
        self.assertIsInstance(result, BundleIdCapability)

    def test_modify_settings_distinguishes_empty_from_omitted(self):
        self.api._api_call.return_value = {'data': self.capability._data}
        for settings, expected in [(None, {}), ([], {'settings': []})]:
            with self.subTest(settings=settings):
                result = self.api.modify_bundle_id_capability(self.capability, settings)
                self.assertIsInstance(result, BundleIdCapability)
                self.assertEqual(self.api._api_call.call_args[0], (
                    BASE_API + '/v1/bundleIdCapabilities/CAPABILITY', HttpMethod.PATCH,
                    {'data': {'id': 'CAPABILITY', 'type': 'bundleIdCapabilities',
                              'attributes': expected, 'relationships': {}}},
                ))

    def test_disable_only_deletes_selected_capability(self):
        self.api.disable_bundle_id_capability(self.capability)
        self.api._api_call.assert_called_once_with(BASE_API + '/v1/bundleIdCapabilities/CAPABILITY', HttpMethod.DELETE)

    def test_apple_error_propagates_without_retry(self):
        self.api._api_call.side_effect = APIError('Already exists', 409)
        with self.assertRaises(APIError) as raised:
            self.api.register_new_bundle_id('Extension', 'com.example.extension', 'UNIVERSAL')
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(self.api._api_call.call_count, 1)

    def test_capability_relationship_resolves_typed_resources(self):
        bundle = BundleId({'id': 'BUNDLE', 'relationships': {'bundleIdCapabilities': {
            'links': {'related': BASE_API + '/v1/bundleIds/BUNDLE/bundleIdCapabilities'},
        }}}, self.api)
        self.api._api_call.return_value = {'data': [self.capability._data]}
        result = [c for c in bundle.bundleIdCapabilities()]
        self.assertIsInstance(result[0], BundleIdCapability)


if __name__ == '__main__':
    unittest.main()
