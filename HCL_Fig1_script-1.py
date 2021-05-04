## load the necessary packages
import numpy as np
import scanpy.api as sc  ### using the scanpy 1.3.7 version
import pandas as pd
import os
import pandas as pd
os.chdir("./HCL/Fig1")


## merge the dataset from different tissues
tissues=["AdultAdrenalGland1","AdultAdrenalGland2","AdultArtery1",         
"AdultAscendingColon1","AdultBladder1","AdultBladder2","AdultBoneMarrow1" ,    
"AdultBoneMarrow2","AdultCerebellum1","AdultCervix1","AdultTransverseColon1" ,         
"AdultDuodenum1", "AdultEpityphlon1","AdultEsophagus1","AdultFallopiantube1",  
"AdultGallbladder1", "AdultHeart1" ,"AdultHeart2", "AdultIleum2" ,         
"AdultKidney2","AdultKidney3","AdultLiver1","AdultLiver2" ,         
"AdultLiver4" ,"AdultLung1","AdultLung2","AdultMuscle1",         
"AdultOmentum1","AdultOmentum2","AdultPancreas1","AdultPeripheralBlood1",
"AdultPeripheralBlood2","AdultPleura1","AdultProstate1","AdultRectum1",         
"AdultSigmoidColon1","AdultSpleen1","AdultStomach1","AdultStomach2","AdultTemporalLobe1",   
"AdultThyroid1","AdultThyroid2","AdultTrachea2","AdultUreter1" ,        
"AdultUterus1","ChorionicVillus1","CordBlood1","CordBloodCD34P1",      
"FetalAdrenalGland2","FetalBrain3","FetalBrain4","FetalBrain5",          
"FetalCalvaria1","FetalFemaleGonad1", "FetalHeart1","FetalIntestine1",      
"FetalIntestine2","FetalIntestine3","FetalKidney3","FetalKidney4",         
"FetalKidney5","FetalLiver1","FetalLung1","FetalMaleGonad1",      
"FetalMaleGonad2","FetalMuscle1", "FetalPancreas1","FetalPancreas2",       
"FetalRib2","FetalRib3","FetalSkin2","FetalSpinalCord1",     
"FetalStomach1","FetalThymus1","FetalThymus2","hESC1","Placenta1" ]

datause= pd.read_table("./dge/AdultAdipose1.rmbatchdge.txt",sep=" ")
for tissue in tissues:
    new=pd.read_table("./dge/" + tissue + '.rmbatchdge.txt',sep=' ')
    datause=pd.merge(datause,new,left_index=True,right_index=True,how='outer')
    print(tissue + " is done")

genes=datause.index
genes=genes.tolist()
cells=datause.columns
cells=cells.tolist()
cells=pd.DataFrame(columns=["cell"],data=cells)
cells.to_csv("cells.csv",sep=",",header=False,index=False)
genes=pd.DataFrame(columns=["gene"],data=genes)
genes.to_csv("genes.csv",sep=",",header=False,index=False)
datause=datause.fillna(0)
datause.to_csv('datause.csv',sep='\t',header=False,index=False)

datause.shape
##451613 × 38360


## load the data
%%time
adata=sc.read_csv("./datause.csv",delimiter='\t').transpose()
adata.var_names = pd.read_csv('./genes.csv', header=None)[0]
adata.obs_names = pd.read_csv('./cells.csv', header=None)[0]
adata.obs['tissue']=pd.read_csv('./cellanno_new.csv',sep=",",header=None)[0].values
mito_genes = [name for name in adata.var_names if name.startswith('MT-')]
adata[:, mito_genes]=0

adata.write('./HCL_scanpy1.h5ad')


## Filter the genes
sc.pp.filter_genes(adata, min_cells=20)
sc.pp.filter_cells(adata, min_genes=0)
adata.obs['n_counts'] = adata.X.sum(axis=1)


## Filter the cells
sc.pl.violin(adata, ['n_genes', 'n_counts'],jitter=0.4, multi_panel=True)
#sc.pl.scatter(adata, x='n_counts', y='percent_mito')
sc.pl.scatter(adata, x='n_counts', y='n_genes')


## Logarithmize the data.
sc.pp.normalize_per_cell(adata, counts_per_cell_after=1e4)
adata.raw = sc.pp.log1p(adata, copy=True)
adata.write('./HCL_scanpy2.h5ad')

## Choose variable genes
adata=sc.read("./HCL_scanpy2.h5ad")
filter_result = sc.pp.filter_genes_dispersion(adata.X, min_mean=0.001, max_mean=15, min_disp=0.5)
sc.pl.filter_genes_dispersion(filter_result)
adata = adata[:, filter_result.gene_subset]
adata.shape()
##451613 × 3118


## Regress out effects of total counts per cell and the percentage of mitochondrial genes expressed. Scale the data to unit variance.
sc.pp.log1p(adata)
sc.pp.regress_out(adata, ['n_counts','ngenes'])

## scale the data
sc.pp.scale(adata, max_value=10)


## PCA
sc.tl.pca(adata, n_comps=100)
sc.pl.pca_loadings(adata)
adata.obsm['X_pca'] *= -1  # multiply by -1 to match Seurat, 
sc.pl.pca_scatter(adata, color='COL1A1') # visualize

## Choose sigificant PCs
sc.pl.pca_variance_ratio(adata, log=True,  show=100,n_pcs=100)


## Computing the neighborhood graph and do t-sne
sc.pp.neighbors(adata, n_neighbors=10,n_pcs=50)
sc.tl.louvain(adata, resolution=4)
sc.tl.tsne(adata,use_fast_tsne=True,n_jobs=20,perplexity=100,n_pcs=50)
sc.pl.tsne(adata, color='louvain',size=8,legend_loc="on data")
sc.pl.tsne(adata, color='louvain',size=8)
sc.pl.tsne(adata, color='tissue',size=8,legend_loc="on data")
sc.pl.tsne(adata, color='tissue',size=8)

adata.write('./HCL_scanpy_pc50.h5ad')

### change the cluster name
new_cluster_names = list(range(1,103))
adata.rename_categories('louvain', new_cluster_names)

## Find marker genes using wilcoxon test
sc.tl.rank_genes_groups(adata, 'louvain', method='wilcoxon')
result = adata.uns['rank_genes_groups']
groups = result['names'].dtype.names
pd.DataFrame(
    {group + '_' + key[:1]: result[key][group]
    for group in groups for key in ['names', 'logfoldchanges','scores', 'pvals', 'pvals_adj']}).to_csv("HCL102_markers_wilcoxon.csv")
adata.write('./HCL_scanpy_pc50_markers_wilcoxon.h5ad', compression='gzip')

