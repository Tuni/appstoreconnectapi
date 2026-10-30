App Store Connect Api
====

This is Python a wrapper around the Apple App Store Api : https://developer.apple.com/documentation/appstoreconnectapi

So far, it only handles token generation / expiration and defines a few routes.

## Bundle IDs and capabilities

These methods use the official App Store Connect API. Authenticate with an API
key that can manage Certificates, Identifiers & Profiles for the intended team.
Examples follow the repository's existing module import convention:

```python
from api import Api

api = Api(key_id, key_file, issuer_id)

# Read-only inventory. Apple's identifier filter may return prefix matches;
# compare identifiers exactly before choosing a resource.
bundles = list(api.list_bundle_ids(filters={'identifier': 'com.example.app.extension'}))
bundle = next(b for b in bundles if b.identifier == 'com.example.app.extension')
bundle = api.read_bundle_id(bundle.id)
capabilities = list(api.list_bundle_id_capabilities(bundle.id))
capability = api.read_bundle_id_capability(capabilities[0].id)

# Explicit writes; review and authorize each operation in the calling tool.
bundle = api.register_new_bundle_id(
    name='Example Extension',
    identifier='com.example.app.extension',
    platform='UNIVERSAL',
)
capability = api.enable_bundle_id_capability(bundle, 'APP_GROUPS')
bundle = api.modify_bundle_id(bundle, name='Renamed Example Extension')
```

`read_bundle_id` and `list_bundle_id_capabilities` take Apple's resource ID,
not the reverse-domain bundle identifier. Write methods take the returned
`BundleId` or `BundleIdCapability` resource objects. Registration accepts an
optional `seedId`; normally let Apple choose the account's prefix.

For configurable capabilities, pass Apple's `settings` list to
`enable_bundle_id_capability` or `modify_bundle_id_capability`. `None` omits the
attribute; `[]` sends an explicit empty list. `disable_bundle_id_capability`
deletes the capability. These methods make explicit API calls; they do not
check for existing resources, retry writes, copy configuration between teams,
or obtain user authorization. Callers must handle those decisions, including
ambiguous write failures, before retrying. Apple errors propagate as `APIError`.

Capability changes can invalidate provisioning profiles; regenerate them before
future signing. These methods do not generate profiles or certificates.

Enabling `APP_GROUPS` does **not** create an App Group or associate its identifier
with a bundle ID. Group registration and assignment remain an Apple Developer
portal step; this wrapper does not invent unsupported public API endpoints.

## Offline tests

From the repository root, using an environment with the existing dependencies:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```

Tests simulate API responses and require no credentials or Apple network access.
