from setuptools import setup

setup(
    name='curobot',
    version='0.1',
    packages=["curobot",],
    url='http://github.com/emre/curobot',
    license='MIT',
    author='emre yilmaz',
    author_email='mail@emreyilmaz.me',
    description='Curation bot for steem network',
    entry_points={
        'console_scripts': [
            'curobot = curobot.curobot:main',
        ],
    },
    install_requires=["dataset", "steem-dshot", "pymysql"]
)
