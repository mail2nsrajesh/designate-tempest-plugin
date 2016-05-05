# Copyright 2016 Hewlett Packard Enterprise Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import functools

from oslo_log import log as logging
from oslo_serialization import jsonutils as json
from tempest.lib.common import rest_client
from tempest.lib import exceptions as lib_exc
from six.moves.urllib import parse as urllib

from designate_tempest_plugin.common.models import ZoneFile

LOG = logging.getLogger(__name__)


def handle_errors(f):
    """A decorator that allows to ignore certain types of errors."""

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        param_name = 'ignore_errors'
        ignored_errors = kwargs.get(param_name, tuple())

        if param_name in kwargs:
            del kwargs[param_name]

        try:
            return f(*args, **kwargs)
        except ignored_errors as e:
            # Silently ignore errors as requested
            LOG.debug('Ignoring exception of type %s, as requested', type(e))

    return wrapper


class DnsClientBase(rest_client.RestClient):
    """Base Tempest REST client for Designate API"""

    uri_prefix = ''

    def serialize(self, object_dict):
        return json.dumps(object_dict)

    def deserialize(self, resp, object_str):
        if 'application/json' in resp['content-type']:
            return json.loads(object_str)
        elif 'text/dns' in resp['content-type']:
            return ZoneFile.from_text(object_str)
        else:
            raise lib_exc.InvalidContentType()

    def expected_success(self, expected_code, read_code):
        # the base class method does not check correctly if read_code is not
        # an int. warn about this and cast to int to avoid silent errors.
        if not isinstance(read_code, int):
            message = ("expected_success(%(expected_code)r, %(read_code)r) "
                       "received not-int read_code %(read_code)r" %
                       {'expected_code': expected_code,
                        'read_code': read_code})
            LOG.warn(message)
        return super(DnsClientBase, self).expected_success(
            expected_code=expected_code, read_code=int(read_code),
        )

    def get_uri(self, resource_name, uuid=None, params=None):
        """Get URI for a specific resource or object.
        :param resource_name: The name of the REST resource, e.g., 'zones'.
        :param uuid: The unique identifier of an object in UUID format.
        :param params: A Python dict that represents the query paramaters to
                       include in the request URI.
        :returns: Relative URI for the resource or object.
        """
        uri_pattern = '{pref}/{res}{uuid}{params}'

        uuid = '/%s' % uuid if uuid else ''
        params = '?%s' % urllib.urlencode(params) if params else ''

        return uri_pattern.format(pref=self.uri_prefix,
                                  res=resource_name,
                                  uuid=uuid,
                                  params=params)

    def _create_request(self, resource, object_dict=None, params=None,
                        headers=None, extra_headers=False):
        """Create an object of the specified type.
        :param resource: The name of the REST resource, e.g., 'zones'.
        :param object_dict: A Python dict that represents an object of the
                            specified type.
        :param params: A Python dict that represents the query paramaters to
                       include in the request URI.
        :param headers (dict): The headers to use for the request.
        :param extra_headers (bool): Boolean value than indicates if the
                                     headers returned by the get_headers()
                                     method are to be used but additional
                                     headers are needed in the request
                                     pass them in as a dict.
        :returns: A tuple with the server response and the deserialized created
                 object.
        """
        body = self.serialize(object_dict)
        uri = self.get_uri(resource, params=params)

        resp, body = self.post(uri, body=body, headers=headers,
                               extra_headers=extra_headers)
        self.expected_success([201, 202], resp.status)

        return resp, self.deserialize(resp, body)

    def _show_request(self, resource, uuid, headers=None, params=None):
        """Gets a specific object of the specified type.
        :param resource: The name of the REST resource, e.g., 'zones'.
        :param uuid: Unique identifier of the object in UUID format.
        :param params: A Python dict that represents the query paramaters to
                       include in the request URI.
        :returns: Serialized object as a dictionary.
        """
        uri = self.get_uri(resource, uuid=uuid, params=params)

        resp, body = self.get(uri, headers=headers)

        self.expected_success(200, resp.status)

        return resp, self.deserialize(resp, body)

    def _list_request(self, resource, params=None):
        """Gets a list of objects.
        :param resource: The name of the REST resource, e.g., 'zones'.
        :param params: A Python dict that represents the query paramaters to
                       include in the request URI.
        :returns: Serialized object as a dictionary.
        """
        uri = self.get_uri(resource, params=params)

        resp, body = self.get(uri)

        self.expected_success(200, resp.status)

        return resp, self.deserialize(resp, body)

    def _put_request(self, resource, uuid, object_dict, params=None):
        """Updates the specified object using PUT request.
        :param resource: The name of the REST resource, e.g., 'zones'.
        :param uuid: Unique identifier of the object in UUID format.
        :param object_dict: A Python dict that represents an object of the
                            specified type
        :param params: A Python dict that represents the query paramaters to
                       include in the request URI.
        :returns: Serialized object as a dictionary.
        """
        body = self.serialize(object_dict)
        uri = self.get_uri(resource, uuid=uuid, params=params)
        resp, body = self.put(uri, body=body)

        self.expected_success([200, 202], resp.status)

        return resp, self.deserialize(resp, body)

    def _update_request(self, resource, uuid, object_dict, params=None):
        """Updates the specified object using PATCH request.
        :param resource: The name of the REST resource, e.g., 'zones'
        :param uuid: Unique identifier of the object in UUID format.
        :param object_dict: A Python dict that represents an object of the
                             specified type.
        :param params: A Python dict that represents the query paramaters to
                       include in the request URI.
        :returns: Serialized object as a dictionary.
        """
        body = self.serialize(object_dict)
        uri = self.get_uri(resource, uuid=uuid, params=params)

        resp, body = self.patch(uri, body=body)

        self.expected_success([200, 202], resp.status)

        return resp, self.deserialize(resp, body)

    def _delete_request(self, resource, uuid, params=None):
        """Deletes the specified object.
        :param resource: The name of the REST resource, e.g., 'zones'.
        :param uuid: The unique identifier of an object in UUID format.
        :param params: A Python dict that represents the query paramaters to
                       include in the request URI.
        :returns: A tuple with the server response and the response body.
        """
        uri = self.get_uri(resource, uuid=uuid, params=params)

        resp, body = self.delete(uri)
        self.expected_success([202, 204], resp.status)
        if resp.status == 202:
            body = self.deserialize(resp, body)

        return resp, body