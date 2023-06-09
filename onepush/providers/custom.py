from ..core import Provider


class Custom(Provider):
    name = 'custom'

    _params = {'required': ['url'], 'optional': ['method', 'datatype', 'data']}

    def _prepare_url(self, url: str, **kwargs):
        self.url = url
        return self.url

    def _prepare_data(self,
                      method: str = 'post',
                      datatype: str = 'data',
                      data: dict = None,
                      **kwargs):
        self.method = method
        self.datatype = datatype
        self.data = data
        return self.data
