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
    name = 'amazon_products_free_proxies'
    allowed_domains = ['amazon.com', 'api.scraperapi.com']
    page = 1

    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            'scrapy_fake_useragent.middleware.RandomUserAgentMiddleware': 400,
            'scrapy_fake_useragent.middleware.RetryUserAgentMiddleware': 401,
            'rotating_proxies.middlewares.RotatingProxyMiddleware': 610,
            'rotating_proxies.middlewares.BanDetectionMiddleware': 620,
        },
        "FAKEUSERAGENT_PROVIDERS": [
            'scrapy_fake_useragent.providers.FakeUserAgentProvider',
            'scrapy_fake_useragent.providers.FakerProvider',
            'scrapy_fake_useragent.providers.FixedUserAgentProvider',
        ],
        "RETRY_TIMES": 10,
        "RETRY_HTTP_CODES": [500, 503, 504, 400, 403, 404, 408],
        "ROTATING_PROXY_LIST_PATH": './free_proxies.txt'
    }

    def __init__(self):
        # define all of the xpaths here
        self.getAllProducts = '//*[@data-component-type="s-search-result"]'

    # Debugging: Product Details Page
    def start_requests(self):
        # sold by amazon = True
        url = 'https://www.amazon.com/Keurig-K55-K-Classic-Coffee-Programmable/dp/B018UQ5AMS/ref=sr_1_19?dchild=1&low_price=100&qid=1602696359&refinements=p_36%3A1253526011&rnid=386465011&s=home-garden&sr=1-19'
        # sold by amazon = False
        # url = 'https://www.amazon.com/Shark-IZ163H-MultiFlex-Self-Cleaning-Technology/dp/B088C6VTKY/ref=sr_1_57?dchild=1&low_price=100&qid=1602692290&s=home-garden&sr=1-57'
        yield scrapy.Request(url=url, callback=self.parse_product_details)

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

        # TODO: enable for production
        # next_page = response.xpath('//li[@class="a-last"]/a/@href').extract_first()
        #
        # if next_page:
        #     logging.info(next_page)
        #     url = f"https://www.amazon.com{next_page}"
        #     logging.info(url)
        #     yield scrapy.Request(url=get_url(url), callback=self.parse)

        # TODO: Disable for production
        if self.page < 4:
            self.page += 1
            url = paginate_url(self.page)
            logging.info(url)
            yield scrapy.Request(url=get_url(url), callback=self.parse)

    def parse_product_details(self, response):

        def get_sold_by_amazon():
            # declare result variable
            result = None
            # get the node
            node_text = response.text
            # if node
            # remove any extra white space
            if node_text:
                # node_remove_whitespace = node_text.strip()
                # string = " ".join(node_remove_whitespace.split())
                # check to see if text inside node includes "sold by Amazon.com"
                has_text = "Ships from and sold by Amazon.com" in node_text
                # if True set to "true" if False set to "false"
                if has_text:
                    result = "true"
                else:
                    result = "false"
            else:
                result = "false"

            return result

        # Get asin
        # asin = response.meta['asin']
        # is_prime = response.meta['isPrime'] # convert to string true or false lowercase
        # url = response.meta['url']
        # Get title
        # title = response.xpath('//*[@id="productTitle"]/text()').extract_first()

        # Get Images
        # list with only 1 index so that i don't break the current api
        # image_urls = [re.search('"large":"(.*?)"',response.text).groups()[0]]

        # Get price
        # price = response.xpath('//*[@id="priceblock_ourprice"]/text()').extract_first()

        # if not price:
        #     price = response.xpath('//*[@data-asin-price]/@data-asin-price').extract_first() or \
        #             response.xpath('//*[@id="price_inside_buybox"]/text()').extract_first()

        # # Get Variations
        # temp = response.xpath('//*[@id="twister"]')
        # sizes = []
        # colors = []
        # if temp:
        #     s = re.search('"variationValues" : ({.*})', response.text).groups()[0]
        #     json_acceptable = s.replace("'", "\"")
        #     di = json.loads(json_acceptable)
        #     sizes = di.get('size_name', [])
        #     colors = di.get('color_name', [])

        # Get About bullets
        # TODO: Array with each bullet extracted
        # about_bullets = response.xpath('//*[@id="feature-bullets"]//li/span/text()').extract()
        sold_by_amazon = get_sold_by_amazon()

        # TODO: reviews int
        #  totalReviews string
        #  description
        #  sellers
        #  isSellerNameInProductName
        #  inStock
        #  uuid
        #  ean
        #  category
        #  upc
        #  hasBuyBox
        #  isFba
        #  soldBy

        yield {
            # "about_bullets": about_bullets,
            # 'imageUrls': image_urls,
            # 'title': title,
            # 'asin': asin,
            # 'url': url,
            # 'isPrime': is_prime,
            # 'ean': ean,
            # 'description': description,
            # 'category': category,
            # 'upc': upc,
            # 'totalReviews': totalReviews,
            # 'rating': rating,
            # 'hasBuyBox': hasBuyBox,
            # 'isFba': isFba,
            'soldByAmazon': sold_by_amazon,
            # 'soldBy': soldBy,
            # 'bsr': bsr,
            # 'inStock': inStock,
            # 'sellers': sellers,
            # 'variations': variations,
            # 'isSellerNameInProductName': isSellerNameInProductName,
            # 'price': price,
            # 'uuid': uuid,

            # 'availableSizes': sizes,
            # 'availableColors': colors,
        }