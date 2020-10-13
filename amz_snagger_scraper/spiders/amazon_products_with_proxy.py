import scrapy
from urllib.parse import urlencode
import re
import json
import logging
API = '0dabb38ed3e0603f8b4f1a354a443476'

def paginate_url(page):
    home_garden_url = f"https://www.amazon.com/s?i=garden&bbn=3295676011&rh=p_36%3A15000-&qid=1602614531&ref=sr_pg_{str(page)}&page={str(page)}"
    return home_garden_url

def get_url(url):
    payload = {'api_key': API, 'url': url, 'country_code': 'us'}
    proxy_url = 'http://api.scraperapi.com/?' + urlencode(payload)
    return proxy_url

class AmazonSpider(scrapy.Spider):
    name = 'amazon_products_with_proxy'
    allowed_domains = ['amazon.com', 'api.scraperapi.com']
    page = 1

    def __init__(self):
        # define all of the xpaths here
        self.getAllProducts = '//*[@data-component-type="s-search-result"]'

    def start_requests(self):
        url = get_url(home_garden_url)
        yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        products = response.xpath(self.getAllProducts)
        for product in products:

            is_prime = product.xpath('.//*[@aria-label="Amazon Prime"]')
            logging.info(is_prime)

            if not is_prime:

                asin = product.xpath('@data-asin').extract_first()

                product_url = f"https://www.amazon.com/dp/{asin}"

                meta = {
                    "isPrime": is_prime,
                    "asin": asin,
                    "url": product_url
                }
                yield scrapy.Request(url=get_url(product_url), callback=self.parse_product_details, meta=meta)

        # next_page = response.xpath('//li[@class="a-last"]/a/@href').extract_first()
        #
        # if next_page:
        #     logging.info(next_page)
        #     url = f"https://www.amazon.com{next_page}"
        #     logging.info(url)
        #     yield scrapy.Request(url=get_url(url), callback=self.parse)

        if self.page < 4:
            self.page += 1
            url = paginate_url(self.page)
            logging.info(url)
            yield scrapy.Request(url=get_url(url), callback=self.parse)

    def parse_product_details(self, response):

        # Get asin
        asin = response.meta['asin']
        is_prime = response.meta['isPrime']
        url = response.meta['url']
        # Get title
        title = response.xpath('//*[@id="productTitle"]/text()').extract_first()

        # Get Images
        # list with only 1 index so that i don't break the current api
        image_urls = [re.search('"large":"(.*?)"',response.text).groups()[0]]

        # Get price
        price = response.xpath('//*[@id="priceblock_ourprice"]/text()').extract_first()

        if not price:
            price = response.xpath('//*[@data-asin-price]/@data-asin-price').extract_first() or \
                    response.xpath('//*[@id="price_inside_buybox"]/text()').extract_first()

        # Get Variations
        temp = response.xpath('//*[@id="twister"]')
        sizes = []
        colors = []
        if temp:
            s = re.search('"variationValues" : ({.*})', response.text).groups()[0]
            json_acceptable = s.replace("'", "\"")
            di = json.loads(json_acceptable)
            sizes = di.get('size_name', [])
            colors = di.get('color_name', [])

        # Get About bullets
        # TODO: Array with each bullet extracted
        about_bullets = response.xpath('//*[@id="feature-bullets"]//li/span/text()').extract()

        # TODO: reviews int
        #  totalReviews string
        #  description
        #  sellers
        #  isSellerNameInProductName
        #  inStock
        #  uuid
        #  ean
        #  catagory
        #  upc
        #  hasBuyBox
        #  isFba
        #  soldByAmazon
        #  soldBy

        # Get Sellers rank
        bsr = response.xpath('//*[text()="Amazon Best Sellers Rank:"]/parent::*//text()[not(parent::style)]').extract()

        yield {
            "about_bullets": about_bullets,
            'imageUrls': image_urls,
            'title': title,
            'asin': asin,
            'url': url,
            'isPrime': is_prime,
            # 'ean': ean,
            # 'description': description,
            # 'category': category,
            # 'upc': upc,
            # 'totalReviews': totalReviews,
            # 'rating': rating,
            # 'hasBuyBox': hasBuyBox,
            # 'isFba': isFba,
            # 'soldByAmazon': soldByAmazon,
            # 'soldBy': soldBy,
            'bsr': bsr,
            # 'inStock': inStock,
            # 'sellers': sellers,
            # 'variations': variations,
            # 'isSellerNameInProductName': isSellerNameInProductName,
            'price': price,
            # 'uuid': uuid,

            # 'availableSizes': sizes,
            # 'availableColors': colors,
        }