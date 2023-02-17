#!/bin/bash
# ref: https://gitlab.com/gitlab-org/build/CNG/blob/master/cfssl-self-sign/scripts/generate-certificates

hash cfssl 2>/dev/null || { echo >&2 "Required command 'cfssl' is not installed. Aborting."; exit 1; }
hash kubectl 2>/dev/null || { echo >&2 "Required command 'kubectl' is not installed. Aborting."; exit 1; }

# Prepare variables
ALGORITHM=${ALGORITHM:-rsa}
KEY_SIZE=${KEY_SIZE:-2048}
EXPIRY=${EXPIRE:-87600h}

CA_KEY_SIZE=${CA_KEY_SIZE:-4096}
CA_SUBJECT=${CA_SUBJECT:-Example Corporation}
CA_ORG=${CA_ORG:-Example Corporation}
CA_ORG_UNIT=${CA_ORG_UNIT:-Example Corporation self-signed SSL}

CERT_SUBJECT=${CERT_SUBJECT:-Example Corporation}
CERT_DOMAIN=${CERT_DOMAIN:-example.com}
CERT_NAME=${CERT_NAME:-example-com}

OUTPUT_DIR=$(mktemp -d /tmp/tls-selfsigned-cert-XXXXXX)

test -d $OUTPUT_DIR || mkdir -p $OUTPUT_DIR
pushd $OUTPUT_DIR

# Output the version
echo "cfssl version:"
cfssl version

echo "ca-config.json:"
tee ca-config.json  <<CA_CONFIG
{
  "signing": {
    "default": {
      "expiry": "${EXPIRY}"
    },
    "profiles": {
      "www": {
        "usages": [
          "signing",
          "cert sign",
          "key encipherment",
          "server auth"
        ],
        "expiry": "${EXPIRY}"
      }
    }
  }
}
CA_CONFIG

echo "ca-csr.json:"
tee ca-csr.json <<CA_CSR
{
  "CN": "${CA_SUBJECT}",
  "key": {
    "algo": "${ALGORITHM}",
    "size": ${CA_KEY_SIZE}
  },
  "names": [
    {
      "O": "${CA_ORG}",
      "OU": "${CA_ORG_UNIT}"
    }
  ]
}
CA_CSR

echo "wildecard-csr.json:"
tee wildcard-csr.json <<WILDCARD_CSR
{
  "CN": "${CERT_SUBJECT}",
  "hosts": [
    "${CERT_DOMAIN}",
    "*.${CERT_DOMAIN}"
  ],
  "key": {
    "algo": "${ALGORITHM}",
    "size": ${KEY_SIZE}
  }
}
WILDCARD_CSR

# Generate CA Cert
echo "Generating CA"
cfssl gencert -initca ca-csr.json | cfssljson -bare ca

# Generate Wildcard Cert
echo "Generating Wildcard certificate"
cfssl gencert \
  -ca=ca.pem -ca-key=ca-key.pem \
  --config=ca-config.json \
  --profile=www \
  wildcard-csr.json | cfssljson -bare wildcard

kubectl create secret tls ssl-${CERT_NAME} \
    --cert wildcard.pem \
    --key wildcard-key.pem \
    --dry-run=client -oyaml > ssl-${CERT_NAME}.yaml

popd

echo "kubectl apply -f ssl-${CERT_NAME}.yaml"
echo "kubectl get secret ssl-${CERT_NAME} -o=jsonpath='{.data.tls\.crt}' | base64 -d | cfssl certinfo -cert -"

echo "OUTPUT_DIR: $OUTPUT_DIR"
