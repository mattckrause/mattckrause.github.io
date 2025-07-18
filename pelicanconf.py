AUTHOR = "Matt Krause"
SITENAME = "Matt Krause"
SITETITLE = "Matt Krause"
SITESUBTITLE = "Matt Krause's personal blog"
SITEDESCRIPTION = "Matt Krause's personal blog"
SITELOGO = "/images/MKLogo.png"
FAVICON = "/images/favicon.png"

PATH = "content"
STATIC_PATHS = ["images"]
TIMEZONE = 'America/Denver'
DEFAULT_LANG = 'EN'

# Feed generation is usually not desired when developing
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None
FEED_ALL_ATOM = "feeds/all.atom.xml"
CATEGORY_FEED_ATOM = "feeds/{slug}.atom.xml"

#main menu
MAIN_MENU = True
# Social widget
SOCIAL = (
    ("bluesky", "https://bsky.app/profile/mattckrause.com"),
    ("github", "https://www.github.com/mattckrause"),
    ("linkedin", "https://www.linkedin.com/in/matthew-krause/"),
)

MENUITEMS = (
    ("Archives", "/archives.html"),
    ("Categories", "/categories.html"),
    ("Tags", "/tags.html"),
)

DEFAULT_PAGINATION = 5
DEFAULT_CATEGORY = "blog"
PYGMENTS_STYLE = "monokai"

#theme
THEME = "theme/Flex/"
