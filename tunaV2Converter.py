from opshin.prelude import *
from pycardano import *
from staticVars import *

#REWARD REDEEMER
@dataclass()
class Lock(PlutusData):
    CONSTR_ID = 1
    lockOutputIndex: int
    convertAmount: int
#MINT REDEEMER
@dataclass()
class Mint(PlutusData):
    CONSTR_ID = 2
#SPEND REDEEMER
@dataclass()
class Spend(PlutusData):
    CONSTR_ID = 1
    zero: int #just 0
#SPEND#DATUM
@dataclass()
class SpendDatum(PlutusData):
    CONSTR_ID = 0 
    blockHeight: int
    redeemAmount: int

hdwallet = HDWallet.from_mnemonic(SEED)
hdwallet_stake = hdwallet.derive_from_path("m/1852'/1815'/0'/2/0")
stake_public_key = hdwallet_stake.public_key
stake_vk = PaymentVerificationKey.from_primitive(stake_public_key)
hdwallet_spend = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
spend_public_key = hdwallet_spend.public_key
payment_vkey = PaymentVerificationKey.from_primitive(spend_public_key)
payment_skey = ExtendedSigningKey.from_hdwallet(hdwallet_spend)
stake_vkey = PaymentVerificationKey.from_primitive(stake_public_key)

#Context
net = Network.MAINNET
chain_context = OgmiosV6ChainContext(OGMIOS_IP_MNET,network=net)
#User
address = Address(payment_vkey.hash(),stake_vkey.hash(),network=net)
userUtxos = chain_context.utxos(address)
#TunaPolicies
lockPolicy = '33443d66138f9609e86b714ff5ba350702ad7d4e476e4cba40cae696'
lockNFT =  MultiAsset.from_primitive({bytes.fromhex(lockPolicy): {b'lock_state': 1}})
v1Policy = '279f842c33eed9054b9e3c70cd6a3b32298259c24b78b895cb41d91a'
v2Policy = 'c981fc98e761e3bb44ae35e7d97ae6227f684bcb6f50a636753da48e'
#Contract
forkScriptRef = Address.from_primitive('addr1q8nyjvt9gjx2vrsqvvafvc69027kfcpzmz4auhjqc29zlg0zn67kl6fmpsqlyd7d3qup3zy5ce3ldc82mta29cwnmawq2mk9ux')
scriptRef = Address.from_primitive('addr1qytemxekk4mtad3jta9kwdu5ymgpzrn54250s79zqqeslpcdj23fymx8ledsa2nakuqzd6tad5le4x8yuefzfrsumv2sn0ada5')
forkValidatorAddress = Address.from_primitive('addr1wye5g0txzw8evz0gddc5lad6x5rs9ttaferkun96gr9wd9sj5y20t')

userV1Tokens = 0
for n in userUtxos:
    if n.output.amount.multi_asset:
            for asset in n.output.amount.multi_asset:
                if asset.payload.hex() == v1Policy:
                    userV1Tokens  += n.output.amount.multi_asset.data[ScriptHash.from_primitive(v1Policy)][AssetName(b'TUNA')]

print(f'You Have {userV1Tokens} Tuna V1')                   
    

refScriptUtxos = chain_context.utxos(scriptRef)
refUtxos = []
for n in refScriptUtxos:
	if n.input.transaction_id.payload.hex() == '55897091192254abbe6501bf4fd63f4d9346e9c2f5300cadfcbe2cda25fd6351':
		refUtxos.append(n)
	elif n.input.transaction_id.payload.hex() == '80874829afb2cb34e23d282d763b419e26e9fb976fe8a7044eebbdf6531214b7' and n.input.index == 0:
		refUtxos.append(n)

scriptUtxos = chain_context.utxos(forkValidatorAddress)
for n in scriptUtxos:
    if n.output.amount.multi_asset:
        assets = n.output.amount.multi_asset
        if len(assets) > 1:
            for a in assets:
                if lockPolicy == a.payload.hex():
                    lockUtxo = n
    if n.output.datum:
        rawPlutus = RawPlutusData.from_cbor(n.output.datum.cbor)
        lockedV1In = rawPlutus.data.value[1]
        



tunaToConvert = 5000000000
tunaToLock = lockedV1In + tunaToConvert
#Redeemers
spendRedeemer =  Redeemer(Spend(0))
withdrawRedeemer = Redeemer(Lock(0,tunaToConvert))
unlockDatum = SpendDatum(30512,tunaToLock)
mintRedeemer = Redeemer(Mint())   
#tunaToConvert

v2Tokens =  MultiAsset.from_primitive({bytes.fromhex(v2Policy): {b'TUNA': tunaToConvert}})
v1TokensOut = MultiAsset.from_primitive({bytes.fromhex(v1Policy): {b'TUNA': tunaToLock}})
minVal = min_lovelace_post_alonzo(TransactionOutput(address, Value(1000000, v2Tokens), datum=unlockDatum),chain_context)            
#Builder
builder = TransactionBuilder(chain_context)
builder.add_input_address(address)
#withdraw
withdrawalAddress = Address.from_primitive('stake17ye5g0txzw8evz0gddc5lad6x5rs9ttaferkun96gr9wd9sw7yvne')
builder.withdrawals = Withdrawals({bytes(withdrawalAddress):0})
builder.add_withdrawal_script(refUtxos[0],withdrawRedeemer)
#builder.add_output(TransactionOutput(address,Value(minVal,v2Tokens)))
builder.reference_inputs.add(refScriptUtxos[0])
builder.reference_inputs.add(refScriptUtxos[1])
#spendValidator
builder.add_script_input(lockUtxo, script=refUtxos[0], redeemer=spendRedeemer)
builder.add_output(TransactionOutput(forkValidatorAddress,Value(minVal,v1TokensOut), datum=unlockDatum))
#mint() or mint?
builder.add_minting_script(refUtxos[1],mintRedeemer)
builder.mint = v2Tokens
signed_tx = builder.build_and_sign([payment_skey], address)
