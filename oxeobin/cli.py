import click
import json
import os
from oxeobin.make_project import ProjectBuilder
from oxeobin.sync_project import SyncProject

@click.group()
def cli():
    pass


@cli.command()
@click.argument('name')
@click.option('--projects_root', type=str, default=os.path.join(os.getcwd(),'projects'))
def initialise_project(name, projects_root):
    """ Initialise the project db and admin user.
    
    args
    ----
    name (str): The name of the project
    --projects_root (str): The root directory of the project
    
    returns
    -------
    1
    """
    
    os.environ['PROJECTFILE'] = os.path.join(projects_root,name,name+'.json')
    from iris import app, db, create_default_admin
    
    create_default_admin(app,db)
    
    return 1


@cli.command()
@click.argument('constellation')
@click.argument('tiles')
@click.argument('name')
@click.argument('n_samples', type=int)
@click.argument('storage_root')
@click.option('--sampling', type=str, default='random')
@click.option('--projects_root', type=str, default=os.path.join(os.getcwd(),'projects'))
@click.option('--cfg', default=None)
def make_project(constellation, tiles, name, n_samples, storage_root, sampling, projects_root, cfg):
    """ 
    Set up a new labelling project.
    
    args
    ----
    constellation (str): The constellation to label in this project
    tiles (str): The list of tiles to label, comma-separated
    name (str): The name of the labelling project
    n_samples (str): The number of samples to label (either in total or per tile, as defined by --sampling)
    storage_root (str): The root of the GCS path to get data from
    port (int): The port to host the labelling project at
    --sampling (str): The sampling strategy, one of [random, random_in_tiles], default is 'random'
    --projects_root (str): The root of the project directories, default is '$PWD/projects'
    --cfg (str): The path to a new iris config file for the labelling project, defaults to <constellation>.json
    
    
    returns
    -------
    1
    """

    if os.path.exists(tiles):
        tiles = json.load(open(tiles,'r'))
    else:
        tiles = tiles.split(',')

    ProjectBuilder(
        constellation=constellation,
        tiles=tiles,
        name=name,
        n_samples=n_samples,
        storage_root=storage_root,
        sampling=sampling,
        projects_root=projects_root,
        cfg=cfg
    ).build()
    
    return 1
    

@cli.command()
@click.argument('project_root')
@click.argument('storage_root')
@click.argument('mask_name')
def sync_project(project_root, storage_root, mask_name):
    """
    Sync the mask results from a project to the cloud.
    
    args
    ----
    project_root (str): The root path of the project (contains, config.json, images, and .iris)
    storage_root (str): The root of the cloud storage e.g. "gs://<bucket>/<somedirectory>"
    mask_name (str): The name of the mask to create
    
    returns
    -------
    1
    """
    
    kept_metadata = SyncProject(
        project_root = project_root, 
        storage_root = storage_root, 
        mask_name = mask_name
    ).run()

    project_name = project_root.split('/')[-1]

    json.dump(kept_metadata, open(f'./{project_name}_{mask_name}.json','w'))
    
    return 1
    
    
if __name__=="__main__":
    cli()
