import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo11-addons-oca-l10n-belarus",
    description="Meta package for oca-l10n-belarus Odoo addons",
    version=version,
    install_requires=[
        'odoo11-addon-currency_rate_update_by_nbb',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
