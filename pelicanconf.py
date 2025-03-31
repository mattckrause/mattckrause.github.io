AUTHOR = "Matt Krause"
SITETITLE = "Matt Krause"
SITESUBTITLE = "Matt Krause's personal blog"
SITEDESCRIPTION = "Matt Krause's personal blog"
SITELOGO = "/images/MKLogo.png"


PATH = "content"
TIMEZONE = 'America/Denver'
DEFAULT_LANG = 'English'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None


MAIN_MENU = True
# Social widget
SOCIAL = (
    ("bluesky", "https://bsky.app/profile/mattckrause.com"),
    ("linkedin", "https://www.linkedin.com/in/matthew-krause/"),
    ("github", "https://www.github.com/mattckrause"),
)

MENUITEMS = (
    ("Archives", "/archives.html"),
    ("Categories", "/categories.html"),
    ("Tags", "/tags.html"),
)

DEFAULT_PAGINATION = 5
DEFAULT_CATEGORY = "blog"
PYGMENTS_STYLE = "monokai"

#Favicon
FAVICON = "images/favicon.png"

THEME = "theme/Flex/"
