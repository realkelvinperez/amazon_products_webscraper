# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class Product(scrapy.Item):
    aboutBullets = scrapy.Field()
    image = scrapy.Field()
    title = scrapy.Field()
    asin = scrapy.Field()
    url = scrapy.Field()
    isPrime = scrapy.Field()
    description = scrapy.Field()
    category = scrapy.Field()
    totalReviews = scrapy.Field()
    rating = scrapy.Field()
    hasBuyBox = scrapy.Field()
    isFba = scrapy.Field()
    soldByAmazon = scrapy.Field()
    soldBy = scrapy.Field()
    bsr = scrapy.Field()
    inStock = scrapy.Field()
    sellers = scrapy.Field()
    variations = scrapy.Field()
    price = scrapy.Field()
    uuid = scrapy.Field()
    isSellerNameInProductName = scrapy.Field()
